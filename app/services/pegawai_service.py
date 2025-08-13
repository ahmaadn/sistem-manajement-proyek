# NOTE: untuk semntara menggunakan data dummy
# implementasi service pegawai akan di kerjakan setalah
# api dari sistem pegawai siap digunakan

from app.schemas.user import UserInfo

FAKE_USERS = [
    {
        "access_token": "dummy_access_token_1",
        "user_id": 1,
        "nama": "Admin",
        "role": "admin",
        "email": "admin@example.com",
        "username": "admin",
        "jabatan": "Kepala Admin",
        "unit_kerja": "Manajemen",
        "alamat": "Jl. Admin No. 1",
    },
    {
        "access_token": "dummy_access_token_2",
        "user_id": 2,
        "nama": "HRD",
        "role": "hrd",
        "email": "hrd@example.com",
        "username": "hrd",
        "jabatan": "HRD Manager",
        "unit_kerja": "HRD",
        "alamat": "Jl. HRD No. 2",
    },
    {
        "access_token": "dummy_access_token_3",
        "user_id": 3,
        "nama": "Pegawai Satu",
        "role": "pegawai",
        "email": "pegawai1@example.com",
        "username": "pegawai1",
        "jabatan": "Staff",
        "unit_kerja": "Operasional",
        "alamat": "Jl. Pegawai No. 3",
    },
    {
        "access_token": "dummy_access_token_4",
        "user_id": 4,
        "nama": "Pegawai Dua",
        "role": "pegawai",
        "email": "pegawai2@example.com",
        "username": "pegawai2",
        "jabatan": "Staff",
        "unit_kerja": "Operasional",
        "alamat": "Jl. Pegawai No. 4",
    },
    {
        "access_token": "dummy_access_token_5",
        "user_id": 5,
        "nama": "Pegawai Tiga",
        "role": "pegawai",
        "email": "pegawai3@example.com",
        "username": "pegawai3",
        "jabatan": "Staff",
        "unit_kerja": "Operasional",
        "alamat": "Jl. Pegawai No. 5",
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

    async def login(self, username_or_email: str, password: str):
        """Login: cek username/email dan password, return access_token jika cocok."""
        # Untuk dummy, password diabaikan, hanya cek username/email
        user = next(
            (
                u
                for u in FAKE_USERS
                if u["username"] == username_or_email
                or u["email"] == username_or_email
            ),
            None,
        )
        if not user:
            return None
        return {"access_token": user["access_token"]}

    def _cast_to_user_info(self, data):
        return UserInfo(
            user_id=data.get("user_id"),
            name=data.get("nama"),
            role=data.get("role"),
            email=data.get("email"),
            username=data.get("username"),
            position=data.get("jabatan"),
            work_unit=data.get("unit_kerja"),
            address=data.get("alamat"),
        )
