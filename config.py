from dataclasses import dataclass, field
from os import getenv
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str = "7778895037:AAEUeDd9nkpajQdag5F_CrFtDM9ZO49GcD8"
    admin_ids: list[int] = field(default_factory=lambda: [516179955])
    database_url: str = "sqlite+aiosqlite:///./bot.db"
    invite_link: str = "https://t.me/+wCwzxVgd4pliYTFi"


settings = Settings()
