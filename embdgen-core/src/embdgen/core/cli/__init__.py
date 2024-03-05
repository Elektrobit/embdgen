# SPDX-License-Identifier: GPL-3.0-only

from typing import Optional, Sequence
from .CLI import CLI

def cli(args: Optional[Sequence[str]] = None) -> None:
    CLI().run(args)
