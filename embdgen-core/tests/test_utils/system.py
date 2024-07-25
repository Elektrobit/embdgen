from functools import lru_cache
import os

@lru_cache
def cur_umask() -> int:
    tmp = os.umask(0o022)
    os.umask(tmp)
    return tmp

def calc_umask(mode: int) -> int:
    return mode & ~cur_umask()
