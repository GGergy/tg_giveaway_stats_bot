import dataclasses
import json
import pathlib
from datetime import datetime

root = pathlib.Path(__file__).resolve().parent.parent
config_path = root / 'assets/secure' / 'config.json'


@dataclasses.dataclass
class Settings:
    tg_bot_token: str
    api_id: int
    api_hash: str
    bot_name: str
    db_file: pathlib.Path
    log_file: pathlib.Path
    messages_file: pathlib.Path
    default_date = datetime(1970, 1, 1)
    pyro_timeout = 5 * 60

    def __post_init__(self):
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            setattr(self, field.name, field.type(value))
            if field.name.endswith("_file"):
                setattr(self, field.name, root / value)


with open(config_path) as file:
    params = json.load(file)
    settings = Settings(**params)
