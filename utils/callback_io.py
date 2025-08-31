from typing import Callable, get_type_hints
from urllib.parse import urlencode, parse_qs

from pyrogram import filters


def call_out(handler: str, **kwargs) -> str:
    res = f"{handler}?{urlencode(kwargs)}"
    if len(res) > 64:
        print("Warning: query params too big")
    return res


class CallbackDataManager:
    def __init__(self, data: str):
        self.data = parse_qs(data[data.find("?") + 1:])

    def __enter__(self):
        return self

    def get(self, key, typeof, default=None):
        value = self.data.get(key)
        if not value:
            return default
        value = value[-1]
        if value == "None":
            return None
        if typeof == bool:
            return value not in ("false", "False", "0")
        return typeof(value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def filter_generator(handler: str) -> Callable:
    return filters.regex(fr"{handler}?\w+")
