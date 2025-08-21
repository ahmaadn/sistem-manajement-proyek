# NOTE: untuk semntara menggunakan data dummy
# implementasi service pegawai akan di kerjakan setalah
# api dari sistem pegawai siap digunakan

from app.schemas.user import PegawaiInfo

FAKE_USERS = [
    {
        "access_token": "dummy_access_token_1",
        "user_id": 1,
        "nama": "Admin",
        "role": "admin",
        "email": "admin@example.com",
        "jabatan": "Kepala Admin",
        "unit_kerja": "Manajemen",
        "alamat": "Jl. Admin No. 1",
        "profile_url": "https://randomuser.me/api/portraits/lego/6.jpg",
    },
    {
        "access_token": "dummy_access_token_2",
        "user_id": 2,
        "nama": "HRD",
        "role": "hrd",
        "email": "hrd@example.com",
        "jabatan": "HRD Manager",
        "unit_kerja": "HRD",
        "alamat": "Jl. HRD No. 2",
        "profile_url": "https://randomuser.me/api/portraits/lego/4.jpg",
    },
    {
        "access_token": "dummy_access_token_3",
        "user_id": 3,
        "nama": "Pegawai Satu",
        "role": "pegawai",
        "email": "pegawai1@example.com",
        "jabatan": "Staff",
        "unit_kerja": "Operasional",
        "alamat": "Jl. Pegawai No. 3",
        "profile_url": "https://randomuser.me/api/portraits/lego/0.jpg",
    },
    {
        "access_token": "dummy_access_token_4",
        "user_id": 4,
        "nama": "Pegawai Dua",
        "role": "pegawai",
        "email": "pegawai2@example.com",
        "jabatan": "Staff",
        "unit_kerja": "Operasional",
        "alamat": "Jl. Pegawai No. 4",
        "profile_url": "https://randomuser.me/api/portraits/lego/2.jpg",
    },
    {
        "access_token": "dummy_access_token_5",
        "user_id": 5,
        "nama": "Pegawai Tiga",
        "role": "pegawai",
        "email": "pegawai3@example.com",
        "jabatan": "Staff",
        "unit_kerja": "Operasional",
        "alamat": "Jl. Pegawai No. 5",
        "profile_url": "https://randomuser.me/api/portraits/lego/8.jpg",
    },
]


class PegawaiService:
    def __init__(self) -> None:
        self.api_url = "https://localhost:3000/"

    async def validate_token(self, token: str) -> bool:
        """Validasi token dengan mencocokkan pada FAKE_USERS."""
        return any(user["access_token"] == token for user in FAKE_USERS)

    async def get_user_info(self, user_id: int):
        """Ambil info user berdasarkan user_id, tanpa access_token."""
        user = next((u for u in FAKE_USERS if u["user_id"] == user_id), None)
        if not user:
            return None
        return self._cast_to_user_info(user.copy())

    async def get_user_info_by_token(self, token: str):
        """Ambil info user berdasarkan access_token, tanpa access_token di hasil."""
        user = next((u for u in FAKE_USERS if u["access_token"] == token), None)
        if not user:
            return None
        return self._cast_to_user_info(user.copy())

    async def login(self, email: str, password: str):
        """Login: cek email dan password, return access_token jika cocok."""
        # Untuk dummy, password diabaikan, hanya cek email
        user = next(
            (u for u in FAKE_USERS if u["email"] == email),
            None,
        )
        if not user:
            return None
        return {"access_token": user["access_token"], "user_id": user["user_id"]}

    def _cast_to_user_info(self, data):
        return PegawaiInfo(
            id=data.get("user_id"),
            name=data.get("nama"),
            employee_role=data.get("role"),
            email=data.get("email"),
            position=data.get("jabatan"),
            work_unit=data.get("unit_kerja"),
            address=data.get("alamat"),
            profile_url=data.get("profile_url"),
        )
