# PDF Tools Mini — Notion Theme + Sign (Drag & Drop)

Aplikasi web mini berbasis **Flask** untuk kerja cepat dengan PDF:
- **Merge** beberapa PDF
- **Split** halaman terpilih
- **Rotate** (all / range)
- **Sign**: tanda tangan **drag-&-drop** di atas preview halaman

UI bergaya **Notion** (warna netral, clean), ringan karena **Tailwind CDN + Alpine.js**, dan preview stabil berkat hasil disimpan sementara di server (bukan `data:` URL).

> ⚠️ Ini **visual signature** (gambar ditempel ke halaman), **bukan** tanda tangan digital bersertifikat (PKI).

---

## ✨ Fitur
- 🎛️ **4 alat**: Merge, Split, Rotate, Sign (drag & drop)
- 📝 **Preview halaman** dengan **PDF.js v2.16.105** (kompatibel di WebView lama; tanpa error “private fields”)
- 🖱️ **Drag & drop** penempatan tanda tangan per halaman, atur lebar (%), plus opsi tanggal otomatis
- 🖋️ **3 mode tanda tangan**: gambar di canvas, upload PNG, atau ketik nama (auto-italic)
- 📄 **Preview hasil** via URL sementara (`/result/<token>.pdf`) — lebih stabil untuk file besar
- 🌓 **Light/Dark** toggle, tema mirip Notion, komponen sederhana (tanpa bundler)

---

## 🧱 Stack
- **Backend:** Flask (Python)
- **PDF processing:** `pypdf`, `reportlab`, `Pillow`
- **Frontend:** Tailwind CSS (CDN), Alpine.js, **PDF.js 2.16.105** (worker match)
- **Preview hasil:** file sementara di direktori temp OS (`/tmp` / `%TEMP%`)

---

## 🚀 Quick Start

### 1) Clone & masuk folder
```bash
git clone https://github.com/<username>/<repo>.git
cd <repo>


python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

python pdf_tools.py
# buka http://localhost:5002/

🖥️ Cara Pakai (Singkat)

Buka aplikasi → pilih tab (Merge / Split / Rotate / Sign).

Merge: pilih beberapa PDF → Gabungkan.

Split: unggah PDF → isi halaman 1,3-5,8 → Ekstrak.

Rotate: unggah PDF → pilih all atau range → pilih derajat → Putar.

Sign:

Unggah PDF → tunggu preview.

Pilih metode tanda tangan: Gambar / Upload / Ketik.

Atur lebar (%) tanda tangan.

Drag kotak tanda tangan ke posisi → klik Apply ke halaman ini.

Ulangi untuk halaman lain → klik Tandatangani.

Lihat hasil di panel bawah (preview iframe). Klik Download.

🧩 Arsitektur Singkat

GET / — halaman utama (UI Notion-like).

POST / — aksi (merge/split/rotate/sign). Hasil disimpan sebagai file sementara dan mengembalikan URL.

GET /result/<token>.pdf — menyajikan hasil PDF (untuk preview & unduh). File dibersihkan otomatis (default 12 jam).

Kunci stabilitas preview:

Bukan data: URL (yang bisa terlalu besar), tapi file sementara via route.

PDF.js v2.16.105 (worker versi sama) → kompatibel di WebView/Browser lama.

⚙️ Konfigurasi

Auto cleanup file hasil: lihat fungsi cleanup_old_results(max_age_hours=12). Ubah angkanya sesuai kebutuhan.

Port: ubah di app.run(..., port=5002).

Tema: color tokens di CSS :root dan .dark:root.

🧪 Kompatibilitas Browser

PDF.js 2.16.105 sengaja dipin agar tidak memakai private fields kelas (yang memicu error di beberapa WebView).

Jika ganti versi PDF.js, pastikan workerSrc versinya sama.

🛟 Troubleshooting

Q: Preview hanya muncul pada operasi tertentu (mis. Rotate)
A: Pastikan versi ini dipakai — hasil disajikan via route /result/<token>.pdf, bukan data: URL. Kalau deploy di reverse proxy, cek ukuran maksimal respons/stream tidak dibatasi.

Q: TypeError: Cannot read private member #…
A: Itu dari PDF.js baru yang pakai private fields. Gunakan 2.16.105 seperti di file ini.

Q: Tanda tangan tidak terlihat di halaman tertentu
A: Pastikan sudah Apply ke halaman itu. Lebar tanda tangan (%) mempengaruhi tinggi; sesuaikan saat halaman berorientasi landscape/portrait.

Q: Font miring tidak muncul pada mode “Ketik”
A: App akan coba ariali.ttf → DejaVuSans-Oblique.ttf → default. Tambahkan font yang kamu mau ke server jika perlu.

🔐 Privasi & Keamanan

Berkas PDF hasil disimpan sementara di direktori temp sistem dengan nama acak (token UUID).

Link hasil tidak diindeks; namun jangan gunakan untuk data sensitif di lingkungan multi-user tanpa hardening tambahan (auth, sandbox, isolasi storage).

Tambahkan reverse proxy (Nginx) & batas ukuran unggah jika dipakai publik.

🧭 Roadmap Ringan

 Apply tanda tangan ke semua halaman sekaligus

 Resize handle pada kotak tanda tangan di preview

 Multiple signature placeholders (Paraf, Nama Jelas, Tanggal)

 Pen & warna untuk “Gambar” (canvas)

🤝 Kontribusi

PR & issue dipersilakan. Mohon jelaskan:

langkah reproduksi,

lingkungan (OS / browser),

contoh file (jika bisa dibagikan).

📄 Lisensi

MIT © 2025 andartelolat
