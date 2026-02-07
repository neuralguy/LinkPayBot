from dataclasses import dataclass, field
from os import getenv
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    #bot_token: str = "7778895037:AAEUeDd9nkpajQdag5F_CrFtDM9ZO49GcD8"
    bot_token: str = "8222451607:AAEORfrBFlnMEFfFeLD7zP46eGDksmvBhzo" #test
    # Главный админ из .env — его нельзя удалить
    main_admin_id: int = 516179955
    # Динамический список админов (заполняется при старте из БД)
    admin_ids: list[int] = field(default_factory=list)
    database_url: str = "sqlite+aiosqlite:///./bot.db"
    invite_link: str = "https://t.me/+wCwzxVgd4pliYTFi"
    # ID канала (числовой, например -1001234567890). Бот должен быть админом канала!
    channel_id: int = -1001234567890
    # Длительность подписки в днях
    subscription_days: int = 30

    def __post_init__(self):
        # Главный админ всегда в списке
        if self.main_admin_id and self.main_admin_id not in self.admin_ids:
            self.admin_ids.append(self.main_admin_id)


settings = Settings()

