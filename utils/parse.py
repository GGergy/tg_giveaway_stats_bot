import re
import datetime

from pyrogram.types import Message

year_prefix = "20"
months = ["январ", "феврал", "март", "апрел", "ма", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"]
full_date_pat = re.compile(r"\d{1,2}[.]\d{1,2}[.]\d{2,4}")
yearless_pat = re.compile(r"\d{1,2}[.]\d{1,2}")
literal_month_pat = re.compile(r"(\d{1,2})\s+" + f"({'|'.join(months)})")
link_pat = re.compile(r"(?:htt(?:p|ps)://)?(?:t.me/|@)([A-z0-9_]+)/?")


def text_or_caption(message: Message):
    if message.text:
        return message.text
    return message.caption


def parse_date(message: Message) -> datetime.datetime:
    text = text_or_caption(message).lower()
    matches = full_date_pat.findall(text)
    now = datetime.datetime.now()
    if matches:
        res = matches[0]
        if len(res[res.rfind(".") + 1:]) == 2:
            res = res[:res.rfind(".") + 1] + year_prefix + res[res.rfind(".") + 1:]
        return datetime.datetime.strptime(res, "%d.%m.%Y")
    matches = yearless_pat.findall(text)
    if matches:
        res = matches[0]
        res += f".{now.year}"
        dt = datetime.datetime.strptime(res, "%d.%m.%Y")
        if dt < now:
            res = res.replace(str(now.year), str(now.year + 1))
            return datetime.datetime.strptime(res, "%d.%m.%Y")
        return dt
    matches = literal_month_pat.findall(text)
    if matches:
        res = matches[0]
        day = res[0]
        month = months.index(res[1]) + 1
        dt = datetime.datetime(year=now.year, month=month, day=int(day))
        if dt < now:
            dt = datetime.datetime(year=now.year + 1, month=month, day=int(day))
        return dt
    raise ValueError


def parse_links(message: Message) -> list[str]:
    links = []
    direct = link_pat.findall(text_or_caption(message))
    links.extend(direct)
    for entities in (message.entities, message.caption_entities):
        if not entities:
            continue
        for entity in entities:
            if entity.url and "t.me" in entity.url:
                groups = link_pat.match(entity.url).groups()
                if groups:
                    links.append(groups[0])
    if not links:
        links.append(message.forward_from_chat.username)
    return links
