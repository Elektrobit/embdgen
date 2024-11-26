import abc
import re
import subprocess
from typing import Dict, Tuple, Callable, Iterable

class SimpleCommandParser(abc.ABC):
    ATTRIBUTE_MAP: Dict[str, Tuple[str, Callable[[str], any]]] = {}

    ok: bool
    error: str

    def __init__(self, command: Iterable[str]) -> None:
        ret = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf8"
        )
        self.error = ret.stderr
        self.ok = ret.returncode == 0

        for line in ret.stdout.splitlines():
            splits = re.split(r"[:=]", line.strip(), 1)
            if len(splits) != 2:
                continue
            key, value = splits
            key, conv = self.ATTRIBUTE_MAP.get(key.strip(), (None, None))
            if not key or not conv:
                continue
            setattr(self, key, conv(value.strip()))
