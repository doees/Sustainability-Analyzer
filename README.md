# Pengembangan Sistem Otomatis Berbasis AI untuk Analisis dan Pemetaan Laporan Keberlanjutan Perusahaan

## Mata Kuliah
**Algoritma Pemrograman II**

## Anggota Kelompok 12: 
1. Khairunnisa Keisha Anjani (NIM. 164241015)
2. Muhammad Firdaus (NIM. 164241030)
3. Mikael Ardiyanta Widyadana Purniawan (NIM. 164241031)
4. Muhammad Iqbal Aulia Fattah (NIM. 164241052)

## Jenis Proyek
**Tugas Akhir**

## Deskripsi Singkat
Proyek ini bertujuan untuk mengembangkan sebuah sistem otomatis berbasis Artificial Intelligence (AI) yang mampu menganalisis laporan keberlanjutan perusahaan dalam format PDF dan memetakan kontennya terhadap standar keberlanjutan internasional, yaitu **GRI (Global Reporting Initiative)** dan **SASB (Sustainability Accounting Standards Board)**.

Sistem dirancang dengan arsitektur **client–server** berbasis RESTful API, di mana pengguna dapat mengakses aplikasi melalui web browser, sementara seluruh proses analisis dan pemrosesan AI dijalankan pada sisi server.

---

## Tujuan Proyek
1. Membangun sistem otomatis yang mampu mengolah laporan keberlanjutan dalam format PDF menjadi data terstruktur.
2. Mengimplementasikan pemetaan konten laporan terhadap standar GRI dan SASB secara otomatis.
3. Mengembangkan algoritma analisis berbasis Natural Language Processing (NLP) dan AI untuk menentukan tingkat kecocokan laporan terhadap standar keberlanjutan.
4. Mengoptimalkan penggunaan token AI dengan menerapkan pencarian berbasis kemiripan (similarity search) menggunakan vector database.

---

## Arsitektur Sistem

Sistem ini menggunakan skenario **dua perangkat (dua laptop)** yang terhubung dalam satu jaringan Wi-Fi:

- **Laptop 1 (Server / Backend)**
  - Menjalankan aplikasi Flask (RESTful API)
  - Melakukan ekstraksi teks dari PDF
  - Melakukan embedding menggunakan Gemini API
  - Menyimpan embedding ke Zilliz Vector Database
  - Mengirim prompt terstruktur (JSONL) ke API AI untuk analisis lanjutan

- **Laptop 2 / Perangkat Pengguna (Client)**
  - Mengakses aplikasi melalui web browser
  - Mengunggah laporan keberlanjutan dan mengisi metadata
  - Melihat hasil analisis secara langsung

Seluruh proses komputasi AI dilakukan pada sisi server, sedangkan perangkat client hanya berfungsi sebagai antarmuka pengguna.

---

## Alur Kerja Sistem
1. Pengguna mengakses website dan mengunggah file PDF laporan keberlanjutan.
2. Sistem melakukan ekstraksi teks dari PDF.
3. Teks dipecah menjadi beberapa bagian (chunking).
4. Setiap chunk diubah menjadi embedding menggunakan Gemini Embedding API.
5. Embedding disimpan ke Zilliz Vector Database.
6. Sistem melakukan similarity search terhadap standar GRI dan SASB.
7. Hanya bagian yang relevan (similarity tinggi) yang dimasukkan ke dalam prompt JSONL.
8. Prompt JSONL dikirim ke API AI untuk analisis dan penilaian.
9. Hasil analisis ditampilkan pada website.

---

## Struktur Folder

