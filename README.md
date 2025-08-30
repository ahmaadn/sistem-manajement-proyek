# Backend Sistem Manajemen Proyek

Backend API untuk sistem manajemen proyek yang dibangun menggunakan FastAPI dan SQLAlchemy dengan dukungan database PostgreSQL.

## 🚀 Fitur

- **FastAPI Framework** - API modern dan cepat dengan dokumentasi otomatis.
- **SQLAlchemy ORM** - Object-Relational Mapping dengan dukungan async.
- **PostgreSQL Database** - Database relational yang robust.
- **Alembic Migrations** - Manajemen skema database yang mudah.
- **JWT Authentication** - Autentikasi dan otorisasi berbasis token yang aman.
- **Manajemen User & Role** - Sistem user dengan role (Admin, Project Manager, Member).
- **Manajemen Proyek & Tugas** - Operasi CRUD penuh untuk proyek dan tugas.
- **Real-time Notifications** - Notifikasi real-time menggunakan Server-Sent Events (SSE), WebSockets, dan Pusher untuk update proyek, tugas, dan anggota tim.
- **Email Integration** - Sistem notifikasi email untuk event penting.
- **File Upload** - Upload file dengan integrasi Cloudinary.
- **Arsitektur Modular** - Kode terstruktur dengan baik menggunakan Class-Based Views dan dependency injection.
- **Event-Driven System** - Menggunakan event untuk menangani side-effect seperti notifikasi.

## 📋 Persyaratan

- Python 3.12+
- PostgreSQL
- UV package manager (recommended) atau pip

## 🛠️ Instalasi

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd backend-sistem-manajement-project
   ```

2. **Setup virtual environment dan install dependencies**
   ```bash
   # Menggunakan UV (recommended)
   uv sync

   # Atau menggunakan pip
   pip install -r requirements.txt
   ```

3. **Setup environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit file `.env` dan sesuaikan konfigurasi database dan variabel lainnya.

4. **Setup database**
   ```bash
   # Jalankan migrasi database
   alembic upgrade head
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
├── api/                 # API routes dan endpoints
│   ├── dependencies/    # Dependency injection
│   └── routes/         # Route handlers
├── core/               # Konfigurasi aplikasi (termasuk real-time)
├── db/                 # Database setup dan migrations
│   ├── models/         # SQLAlchemy models
│   └── migrations/     # Alembic migrations
├── middleware/         # Custom middleware
├── schemas/            # Pydantic schemas
├── services/           # Business logic layer
├── static/            # Static files
├── templates/         # Jinja2 templates
└── utils/             # Utility functions
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

