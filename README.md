# Backend Sistem Manajemen Proyek

Backend API untuk sistem manajemen proyek yang dibangun menggunakan FastAPI (async), SQLAlchemy, dan PostgreSQL. Mendukung manajemen proyek, tugas, anggota tim, notifikasi real-time (SSE, WebSocket, Pusher), audit timeline (perubahan status, judul, assignee), integrasi layanan Pegawai eksternal, upload file ke Cloudinary, serta arsitektur modular dengan pola repository & unit of work.

## 🚀 Fitur

- **FastAPI (Async)** - Kinerja tinggi dengan dokumentasi otomatis.
- **SQLAlchemy ORM (Async)** - Akses database efisien & terstruktur.
- **PostgreSQL** - Database relational yang andal.
- **Alembic Migrations** - Versi skema database terkelola.
- **JWT Authentication** - Keamanan akses berbasis token.
- **Manajemen User & Role** - Admin, Project Manager, Member.
- **Manajemen Proyek & Tugas** - CRUD proyek, tugas, milestone, kategori, lampiran, komentar.
- **Notifikasi Real-time** - SSE & WebSocket; opsi Pusher sebagai driver eksternal.
- **Audit Timeline** - Perubahan status, judul, assignee tugas digabung dengan komentar.
- **Notifikasi User** - Baca/belum dibaca, sortir terbaru/terlama.
- **Pagination & Search User** - Query dengan `per_page` dan `search`.
- **Integrasi Layanan Pegawai** - Pengambilan info user eksternal dengan cache per-request.
- **Email Integration** - Pengiriman email untuk event penting.
- **Upload File Cloudinary** - Penyimpanan media eksternal dengan fallback avatar otomatis.
- **Arsitektur Modular** - CBV, repository, unit of work, dependency injection.
- **Event-Driven** - Event internal untuk notifikasi & side-effect.

## 📋 Persyaratan

- Python 3.12+
- PostgreSQL
- UV package manager (recommended) atau pip
- Akun Cloudinary (untuk upload file)
- Akun Pusher (opsional jika ingin mengaktifkan driver Pusher)

## 🛠️ Instalasi

### 1. Clone repository
```bash
git clone https://gitlab.com/ahmaadn01/backend-sistem-management-proyek.git
cd backend-sistem-manajement-project
```

### 2. Install dependencies
Lokal (development):
```bash
# Menggunakan UV (recommended)
uv sync

# Atau menggunakan pip
pip install -r requirements.txt
```

Produksi (minimal):
```bash
pip install --no-cache-dir -r requirements.txt
```

### 3. Salin & konfigurasi environment
```bash
cp .env.example .env
```
Edit `.env` sesuai kebutuhan:
Wajib dasar:
```
DB_SERVER=127.0.0.1
DB_PORT=xxx
DB_DATABASE=xxx
DB_USERNAME=xxx
DB_PASSWORD=xxx
```
Cloudinary:
```
CLOUDINARY_CLOUD_NAME=xxx
CLOUDINARY_API_KEY=xxx
CLOUDINARY_API_SECRET=xxx
```
Realtime (opsional Pusher):
```
REALTIME_DRIVERS=pusher,sse,websocket
PUSHER_APP_ID=xxx
PUSHER_KEY=xxx
PUSHER_SECRET=xxx
PUSHER_CLUSTER=ap1
PUSHER_SSL=1
```
Integrasi layanan Pegawai eksternal, lihat configuasi url di `app/client/pegawai_client.py`   :
```
BASE_API_PEGAWAI=https://pegawai.example.com
```

### 4. Migrasi database
```bash
alembic upgrade head
```

### 5. (Opsional) Seed data
```bash
uv run python app/seeder.py
```

## 🚀 Menjalankan Aplikasi

### Development
```bash
# Menggunakan FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
# Menggunakan production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Aplikasi akan berjalan di `http://localhost:8000`

## 📚 API Documentation

Setelah aplikasi berjalan, dokumentasi API dapat diakses di:
- **Swagger UI**: `http://localhost:8000/docs`

## 🗂️ Struktur Proyek

```
app/
├── main.py                 # Entry FastAPI
├── seeder.py               # Script seeding opsional
├── sse.py / websocket.py   # Implementasi real-time SSE & WS
├── api/
│   ├── api.py              # Router aggregator
│   ├── dependencies/       # Dependency (auth, repos, services)
│   └── routes/             # Endpoint modular (task, project, user, dll)
├── client/                 # HTTP client ke layanan eksternal (Pegawai)
├── core/                   # Config, realtime driver, settings
├── db/
│   ├── base.py / meta.py   # Deklarasi Base / metadata
│   ├── migrations/         # Alembic migration scripts
│   ├── models/             # SQLAlchemy models
│   ├── repositories/       # Repository pattern
│   └── uow/                # Unit of Work
├── middleware/             # Middleware kustom (context, request)
├── schemas/                # Pydantic schema (user, task, project, dll)
├── services/               # Business logic (task, user, notification, dll)
├── static/                 # Static files (robots.txt)
├── templates/              # Jinja2 templates (pusher test, dll)
├── utils/                  # Helper umum (cloudinary, email, pagination)
└── policies/               # (Jika ada) kebijakan akses / domain rules
```


## 🔧 Database Migrations

```bash
# Membuat migration baru
alembic revision --autogenerate -m "Description"

# Menjalankan migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 📝 License

Project ini menggunakan lisensi MIT. Lihat file `LICENSE` untuk detail lebih lanjut.

