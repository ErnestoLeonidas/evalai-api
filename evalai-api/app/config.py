from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8")

    db_user: str
    db_password: str
    db_dsn: str = "ut9bjwcq3z8a1dug_tp"
    wallet_dir: Path = Path("../wallet")
    wallet_password: str

    @property
    def wallet_path(self) -> Path:
        """Ruta absoluta del wallet; una ruta relativa se toma desde la carpeta del proyecto."""
        ruta = self.wallet_dir if self.wallet_dir.is_absolute() else BASE_DIR / self.wallet_dir
        return ruta.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
