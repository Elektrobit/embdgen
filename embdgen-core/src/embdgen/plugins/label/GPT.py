# SPDX-License-Identifier: GPL-3.0-only

import io
from pathlib import Path

from embdgen.core.region.BaseRegion import BaseRegion
from embdgen.core.utils.SizeType import SizeType
from embdgen.core.label.BaseLabel import BaseLabel

class PMBRHeader(BaseRegion):

    def __init__(self) -> None:
        super().__init__()
        self.name = "PMBR Header"
        self.is_partition = False
        self.start = SizeType(0)
        self.size = SizeType(512)

    def write(self, out_file: io.BufferedIOBase):
        return


class GPTHeader(BaseRegion):

    def __init__(self, name="GPT Header") -> None:
        super().__init__()
        self.name = name
        self.is_partition = False
        self.start = SizeType(512)
        self.size = SizeType(512*33)

    def write(self, out_file: io.BufferedIOBase):
        return

class GPT(BaseLabel):
    """GUID Partition Table (GPT) partition type"""
    LABEL_TYPE = 'gpt'

    GPT_DISK_ID_OFFSET = 0x238

    pmbr_header: PMBRHeader
    gpt_header: GPTHeader
    sgpt_header: GPTHeader

    def __init__(self) -> None:
        super().__init__()
        self.pmbr_header = PMBRHeader()
        self.gpt_header = GPTHeader()
        self.sgpt_header = GPTHeader("Secondary GPT Header")
        self.parts.append(self.pmbr_header)
        self.parts.append(self.gpt_header)

    def prepare(self):
        if self.pmbr_header not in self.parts:
            self.parts.append(self.pmbr_header)
        if self.gpt_header not in self.parts:
            self.parts.append(self.gpt_header)
        super().prepare()
        self.sgpt_header.start = self.parts[-1].start + self.parts[-1].size
        self.parts.append(self.sgpt_header)

    def create_partition_table(self, filename: Path):
        self._create_partition_table(filename, "gpt")

    def __repr__(self) -> str:
        return "GPT:\n  " + "\n  ".join(map(repr, self.parts))
