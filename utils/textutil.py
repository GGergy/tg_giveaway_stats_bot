import pathlib
import re
import sys
from typing import Dict

import polib

from utils.config import settings


textfile = polib.pofile(settings.messages_file)


def compile_msg(message: str, kwargs: Dict[str, str]) -> str:
    for token, value in kwargs.items():
        token = "{{ " + token + " }}"
        if token in message:
            message = message.replace(token, str(value))
        else:
            print("Warning: token " + token[3:-3] + " is not found in message")
    return message


def gettext(key: str, **kwargs) -> str:
    ans = textfile.find(key)
    if ans:
        if kwargs:
            return compile_msg(ans.msgstr, kwargs)
        else:
            return ans.msgstr
    return key


def truncate(text: str, chars: int) -> str:
    if len(text) <= chars:
        return text
    return text[:chars - 3] + "..."


def find_usages(file: pathlib.Path, funcname: str = "gt") -> None:
    with open(file) as rf:
        data = rf.read()

    quotes = r"['" + '"]'
    usages = re.findall(funcname + r"\(" + quotes + r"[A-z0-1_]+" + quotes, data)
    usages = set(map(lambda u: u[len(funcname) + 2:-1], usages))
    total_added = 0
    print("detected", usages)

    with open(settings.messages_file, "a") as wf:
        for usage in set(usages):
            if textfile.find(usage):
                print(usage, "skipped")
                continue

            print(usage, "added")
            total_added += 1
            wf.write(f'\nmsgid "{usage}"\nmsgstr ""\n')

    print(f"\nFound {len(usages)} usages, {len(usages) - total_added} skipped, {total_added} added\n")

    if input("Terminate script? [y/N]: ").lower() == "y":
        sys.exit(0)
