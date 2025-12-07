from pathlib import Path
from datetime import datetime
import os
import json
import re

from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from dotenv import load_dotenv
from pypdf import PdfReader

# --- Load .env ---
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

# --- Setup dasar Flask ---
app = Flask(__name__)

# Konfigurasi dari environment
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")
upload_folder_name = os.getenv("UPLOAD_FOLDER", "uploads")
max_content_mb = int(os.getenv("MAX_CONTENT_LENGTH_MB", "50"))

# Batas ukuran request (dalam byte): default 50 MB
app.config["MAX_CONTENT_LENGTH"] = max_content_mb * 1024 * 1024

# Folder upload PDF
UPLOAD_FOLDER = BASE_DIR / upload_folder_name
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Folder untuk simpan file prompt JSONL
JOBS_DIR = BASE_DIR / "jobs"
PROMPT_DIR = JOBS_DIR / "prompts"
PROMPT_DIR.mkdir(parents=True, exist_ok=True)

# Folder untuk simpan file chunk teks SR (untuk embedding & Zilliz)
DATA_DIR = BASE_DIR / "data"
CHUNKS_DIR = DATA_DIR / "chunks"
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}


def allowed_file(filename):
    """Cek apakah file ber-ekstensi PDF."""
    return "." in filename and Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def extract_pdf_info(saved_path, original_filename):
    """
    Baca PDF untuk info ringan:
    - nama file
    - jumlah halaman
    - cuplikan teks halaman pertama (pendek, untuk UI saja)
    TIDAK kita kirim ke OpenAI.
    """
    pdf_info = {
        "file_name": original_filename,
        "num_pages": None,
        "sample_excerpt": None,
    }

    if saved_path is not None and saved_path.exists():
        try:
            reader = PdfReader(saved_path)
            num_pages = len(reader.pages)
            pdf_info["num_pages"] = num_pages

            if num_pages > 0:
                first_page = reader.pages[0]
                text = (first_page.extract_text() or "").strip().replace("\n", " ")
                if len(text) > 500:
                    text = text[:500] + "..."
                pdf_info["sample_excerpt"] = text or None

        except Exception as parse_err:
            pdf_info["sample_excerpt"] = (
                f"PDF parsing error (ignored in dummy stage): {parse_err}"
            )

    return pdf_info


def extract_pdf_chunks(saved_path, job_id, max_chars=1000, overlap=200):
    """
    Membaca PDF dan memotong teks setiap halaman menjadi beberapa chunk pendek,
    siap untuk di-embedding dan dimasukkan ke Zilliz nanti.

    - max_chars: panjang maksimum 1 chunk (karakter)
    - overlap: jumlah overlap antar chunk supaya konteks tidak terputus total
    """
    chunks = []

    if saved_path is None or not saved_path.exists():
        return chunks

    try:
        reader = PdfReader(saved_path)

        for page_index, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            raw_text = raw_text.strip()
            if not raw_text:
                continue

            # Rapikan whitespace (newline, tab, dll)
            text = re.sub(r"\s+", " ", raw_text)

            start = 0
            local_chunk_idx = 1

            while start < len(text):
                end = start + max_chars
                chunk_text = text[start:end]

                chunk_id = f"{job_id}-p{page_index}-c{local_chunk_idx}"

                chunks.append(
                    {
                        "job_id": job_id,
                        "chunk_id": chunk_id,
                        "page": page_index,
                        "text": chunk_text,
                    }
                )

                if end >= len(text):
                    break

                # Mundur sedikit untuk overlap
                start = end - overlap
                local_chunk_idx += 1

    except Exception as e:
        # Di tahap awal, kalau gagal parsing, kita hanya log ke terminal
        print(f"[WARN] Failed to extract chunks from PDF {saved_path}: {e}")

    return chunks


def save_chunks_json(job_id, chunks):
    """
    Menyimpan daftar chunk ke file JSON:
    data/chunks/<job_id>_chunks.json
    """
    payload = {
        "job_id": job_id,
        "chunks": chunks,
    }

    out_path = CHUNKS_DIR / f"{job_id}_chunks.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return out_path


def slugify(value):
    """
    Ubah nama material topic jadi slug yang aman untuk dipakai di custom_id.
    Contoh: 'GHG Emissions Scope 1' -> 'ghg-emissions-scope-1'
    """
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "topic"


def build_prompt_jsonl(job_id, company_name, report_year, sector, material_topics):
    """
    Membangun file JSONL untuk OpenAI Batch API.
    - 1 baris per material topic
    - Tiap baris sudah dalam format:
      { "custom_id": ..., "method": "POST", "url": "/v1/responses", "body": {...} }
    Di dalam body sudah ada prompt (system + user) dan metadata.
    TIDAK menyertakan teks SR yang panjang, hanya info meta.
    """
    out_path = PROMPT_DIR / f"{job_id}_prompts.jsonl"

    with out_path.open("w", encoding="utf-8") as f:
        for topic in material_topics:
            topic_slug = slugify(topic)
            custom_id = f"{job_id}-{topic_slug}"

            # System prompt
            system_content = (
                "Anda adalah asisten ahli ESG yang membantu memetakan material topic "
                "perusahaan ke standar GRI, SASB, dan ISSB. "
                "Jawaban Anda HARUS selalu dalam format JSON sesuai skema yang diminta, "
                "tanpa teks penjelasan di luar JSON."
            )

            # User prompt (metadata perusahaan + instruksi output JSON)
            user_content = (
                "Berikut adalah konteks analisis material topic.\n\n"
                f"Informasi perusahaan:\n"
                f"- Nama perusahaan: {company_name}\n"
                f"- Tahun laporan: {report_year}\n"
                f"- Sektor / industri: {sector}\n"
                f"- Material topic yang sedang dianalisis: {topic}\n\n"
                "Tugas Anda:\n"
                "1. Berdasarkan pengetahuan Anda tentang standar GRI, SASB, dan ISSB, "
                "pilih indikator yang paling relevan untuk material topic ini.\n"
                "2. Untuk setiap indikator yang relevan, tentukan coverage_status awal sebagai salah satu dari:\n"
                '   - \"Covered\"\n'
                '   - \"Partially Covered\"\n'
                '   - \"Not Covered\"\n'
                "   (Untuk tahap ini, anggap coverage_status sebagai prior kasar berbasis praktik terbaik sektor,\n"
                "    karena teks lengkap laporan keberlanjutan belum disertakan dalam prompt.)\n"
                "3. Berikan catatan singkat (notes) untuk menjelaskan alasan pemilihan indikator tersebut.\n\n"
                "Kembalikan output DALAM BENTUK JSON dengan skema berikut:\n"
                "{\n"
                '  \"material_topic\": string,\n'
                '  \"framework\": string,              // misal: \"GRI\", \"SASB\", \"ISSB\"\n'
                '  \"candidates\": [\n'
                "    {\n"
                '      \"code\": string,              // contoh: \"GRI 302-1\", \"IF-WU-110a.1\"\n'
                '      \"title\": string,\n'
                '      \"coverage_status\": string,   // \"Covered\" | \"Partially Covered\" | \"Not Covered\"\n'
                '      \"notes\": string              // catatan singkat, max ~2 kalimat\n'
                "    }\n"
                "  ]\n"
                "}\n"
                "JANGAN menambahkan teks lain di luar JSON."
            )

            body = {
                "model": "gpt-4.1-mini",  # bisa kamu ganti nanti
                "response_format": {"type": "json_object"},
                "input": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ],
                "metadata": {
                    "job_id": job_id,
                    "company_name": company_name,
                    "report_year": report_year,
                    "sector": sector,
                    "material_topic": topic,
                },
            }

            line = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/responses",
                "body": body,
            }

            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    return out_path


def build_dummy_mappings(material_topics):
    """
    Mapping dummy GRI/SASB seperti sebelumnya.
    Ini hanya untuk tampilan UI sementara sebelum full AI dipakai.
    """
    mappings = []

    for topic in material_topics:
        t_lower = topic.lower()

        if "energy" in t_lower:
            mappings.append(
                {
                    "material_topic": topic,
                    "framework": "GRI",
                    "code": "302-1",
                    "status": "Partial",
                    "pages": "18–21",
                    "recommendation": "Report renewable vs non-renewable; add 302-3 energy intensity target.",
                }
            )
        elif "ghg" in t_lower or "emission" in t_lower:
            mappings.append(
                {
                    "material_topic": topic,
                    "framework": "SASB",
                    "code": "IF-WU-110a.1",
                    "status": "Covered",
                    "pages": "30–33",
                    "recommendation": "Clarify Scope 3 boundary & methodology.",
                }
            )
        elif "waste" in t_lower:
            mappings.append(
                {
                    "material_topic": topic,
                    "framework": "GRI",
                    "code": "306-3",
                    "status": "Partial",
                    "pages": "40–42",
                    "recommendation": "Add breakdown of hazardous vs non-hazardous waste, incl. recovery.",
                }
            )
        elif "labor" in t_lower or "employment" in t_lower:
            mappings.append(
                {
                    "material_topic": topic,
                    "framework": "GRI",
                    "code": "401-1",
                    "status": "Covered",
                    "pages": "50–52",
                    "recommendation": "Disclose turnover rate by gender & age group.",
                }
            )
        else:
            mappings.append(
                {
                    "material_topic": topic,
                    "framework": "GRI",
                    "code": "TBD",
                    "status": "Not Covered",
                    "pages": "-",
                    "recommendation": "No clear disclosure detected; consider adding narrative & KPI for this topic.",
                }
            )

    return mappings


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    """
    Error handler untuk file yang terlalu besar (413).
    """
    return (
        jsonify(
            {
                "status": "error",
                "message": f"File too large. Max {max_content_mb} MB allowed.",
            }
        ),
        413,
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Endpoint utama dari frontend (form HTML).

    Alur:
    - Validasi input
    - Simpan PDF (kalau ada)
    - Ambil info ringan PDF (num_pages, sample_excerpt) -> untuk UI
    - Generate job_id
    - Ekstrak chunk teks -> simpan ke data/chunks/<job_id>_chunks.json (untuk embedding & Zilliz)
    - Build file JSONL prompt untuk OpenAI Batch (/v1/responses) per material topic
    - Buat dummy mapping (sementara)
    - Return JSON ke frontend + path prompt_file + chunks_file
    """
    try:
        company_name = request.form.get("companyName", "").strip()
        report_year = request.form.get("reportYear", "").strip()
        sector = request.form.get("sector", "").strip()
        enable_ocr = request.form.get("enableOCR", "false").lower() == "true"
        topics_raw = request.form.get("materialTopics", "").strip()

        # Validasi sederhana
        if not company_name:
            return jsonify({"status": "error", "message": "Company Name is required"}), 400
        if not report_year:
            return jsonify({"status": "error", "message": "Report Year is required"}), 400
        if not sector:
            return jsonify({"status": "error", "message": "Sector is required"}), 400
        if not topics_raw:
            return jsonify(
                {"status": "error", "message": "At least one material topic is required"}
            ), 400

        material_topics = [t.strip() for t in topics_raw.split(",") if t.strip()]

        # Ambil file
        uploaded_file = request.files.get("reportFile")
        saved_path = None
        original_filename = None

        if uploaded_file and uploaded_file.filename:
            original_filename = uploaded_file.filename
            if not allowed_file(original_filename):
                return jsonify({"status": "error", "message": "Only PDF files are allowed"}), 400

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_name = f"{timestamp}_{Path(original_filename).name}"
            saved_path = UPLOAD_FOLDER / safe_name
            uploaded_file.save(saved_path)

        # Buat job_id untuk identitas analisis ini
        job_id = datetime.now().strftime("JOB-%Y%m%d-%H%M%S")

        # Ekstrak info ringan dari PDF (tanpa teks full)
        pdf_info = extract_pdf_info(saved_path, original_filename)

        # Ekstrak chunk teks untuk keperluan embedding & Zilliz (belum di-embedding di step ini)
        chunks_file_path = None
        if saved_path is not None and saved_path.exists():
            chunks = extract_pdf_chunks(
                saved_path,
                job_id=job_id,
                max_chars=1000,
                overlap=200,
            )
            if chunks:
                chunks_path = save_chunks_json(job_id, chunks)
                chunks_file_path = str(chunks_path)

        # Build file JSONL prompt untuk OpenAI Batch API
        prompt_path = build_prompt_jsonl(
            job_id=job_id,
            company_name=company_name,
            report_year=report_year,
            sector=sector,
            material_topics=material_topics,
        )

        # Dummy mapping (sementara, untuk ditampilkan di UI)
        mappings = build_dummy_mappings(material_topics)

        result = {
            "company_name": company_name,
            "report_year": report_year,
            "sector": sector,
            "enable_ocr": enable_ocr,
            "material_topics": material_topics,
            "file_saved": bool(saved_path),
            "file_path": str(saved_path) if saved_path else None,
            "pdf_info": pdf_info,
            "prompt_file_path": str(prompt_path),   # untuk GPT Batch
            "chunks_file_path": chunks_file_path,   # untuk embedding & Zilliz
            "mappings": mappings,
        }

        return jsonify(
            {
                "status": "success",
                "job_id": job_id,
                "message": "Job received. Prompt JSONL & chunks generated.",
                "result": result,
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

