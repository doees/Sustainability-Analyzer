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
Proyek ini bertujuan untuk membangun sebuah sistem otomatis berbasis Artificial Intelligence (AI) yang mampu mengekstraksi dan menganalisis laporan keberlanjutan perusahaan dalam format PDF, kemudian memetakan isi laporan tersebut ke dalam standar keberlanjutan internasional, yaitu Global Reporting Initiative (GRI) dan Sustainability Accounting Standards Board (SASB).

Sistem ini dirancang menggunakan arsitektur client–server dengan pendekatan RESTful API, di mana pengguna berinteraksi melalui aplikasi berbasis web, sementara seluruh proses analisis data dan pemrosesan AI dilakukan di sisi server.

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


