# Backend Sistem Manajemen Proyek

Backend API untuk sistem manajemen proyek yang dibangun menggunakan FastAPI dan SQLAlchemy dengan dukungan database PostgreSQL.

## 🚀 Fitur

- **FastAPI Framework** - API modern dan cepat dengan dokumentasi otomatis
- **SQLAlchemy ORM** - Object-Relational Mapping dengan dukungan async
- **PostgreSQL Database** - Database relational yang robust
- **Alembic Migrations** - Manajemen skema database
- **JWT Authentication** - Autentikasi dan otorisasi yang aman
- **Email Integration** - Sistem notifikasi email
- **File Upload** - Upload file dengan Cloudinary
- **API Documentation** - Dokumentasi API otomatis dengan Swagger/OpenAPI

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
- **ReDoc**: `http://localhost:8000/redoc`

## 🗂️ Struktur Proyek

```
app/
├── api/                 # API routes dan endpoints
│   ├── dependencies/    # Dependency injection
│   └── routes/         # Route handlers
├── core/               # Konfigurasi aplikasi
├── db/                 # Database setup dan migrations
│   ├── models/         # SQLAlchemy models
│   └── migrations/     # Alembic migrations
├── middleware/         # Custom middleware
├── schemas/            # Pydantic schemas
├── static/            # Static files
├── templates/         # Jinja2 templates
└── utils/             # Utility functions
```

## 🧪 Testing

```bash
# Menjalankan semua test
pytest

# Menjalankan test dengan coverage
pytest --cov=app

# Menjalankan test spesifik
pytest test/test_api/
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

## 🤝 Kontribusi

1. Fork repository
2. Buat feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit perubahan (`git commit -m 'Add some AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Buat Pull Request

## 📝 License

Project ini menggunakan lisensi MIT. Lihat file `LICENSE` untuk detail lebih lanjut.

## 👥 Tim Pengembang

- [Nama Developer] - Initial work

## 📞 Dukungan

Jika ada pertanyaan atau issue, silakan buat issue di repository ini atau hubungi tim pengembang.
