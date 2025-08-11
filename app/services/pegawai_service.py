# NOTE: untuk semntara menggunakan data dummy
# implementasi service pegawai akan di kerjakan setalah
# api dari sistem pegawai siap digunakan


class PegawaiService:
    def __init__(self) -> None:
        self.api_url = "https://localhost:3000/"

    async def validate_token(self, token: str) -> bool:
        return True

    async def get_user_info(self):
        return {
            "user_id": 1,
            "data_pegawai_id": 1,
            "nama": "Lorem Ipsum",
            "role": "admin",
            "jabatan": "",
            "unit_kerja": "",
        }

    async def login(self, username: str, password: str):
        return {
            "access_token": "dummy_access_token",
        }

    async def legalitas_pegawai(self): ...


pegawai_service = PegawaiService()
