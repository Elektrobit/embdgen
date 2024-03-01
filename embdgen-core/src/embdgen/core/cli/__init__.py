# SPDX-License-Identifier: GPL-3.0-only

from typing import Sequence
from embdgen.core.cli.CLI import CLI


def cli(args: Sequence[str] = None) -> None:
    """
    Run command line interface.
    """
    CLI().run(args)
