# SPDX-License-Identifier: GPL-3.0-only

import io
import struct
from typing import Optional
from pathlib import Path

from embdgen.plugins.region.PartitionRegion import PartitionRegion
from embdgen.core.utils.class_factory import Config
from embdgen.core.region.BaseRegion import BaseRegion
from embdgen.core.utils.SizeType import SizeType
from embdgen.core.label.BaseLabel import BaseLabel

class MBRHeader(BaseRegion):
    diskid: Optional[int] = None

    def __init__(self) -> None:
        super().__init__()
        self.name = "MBR Header"
        self.is_partition = False
        self.start = SizeType(0x1b8)
        self.size = SizeType(0x48)

    def write(self, out_file: io.BufferedIOBase):
        if self.diskid:
            out_file.seek(MBR.DISK_ID_OFFSET)
            out_file.write(struct.pack("I", self.diskid))

class EBRHeader(BaseRegion):
    start: SizeType

    def __init__(self) -> None:
        super().__init__()
        self.name = "EBR Header"
        self.is_partition = False
        self.size = SizeType(0x200)

    def write(self, out_file: io.BufferedIOBase):
        return

@Config('diskid', optional=True)
class MBR(BaseLabel):
    """
    Master Boot Record (DOS) partition type

    If more than 4 partitions are configured, all partitions starting
    at the third will be created as extended partitions automatically.
    """
    LABEL_TYPE = 'mbr'

    DISK_ID_OFFSET = 0x1B8

    mbr_header: MBRHeader

    def __init__(self) -> None:
        super().__init__()
        self.mbr_header = MBRHeader()
        self.parts.append(self.mbr_header)

    @property
    def diskid(self) -> Optional[int]:
        """Diskid value (part of the partition table metadata)"""
        return self.mbr_header.diskid

    @diskid.setter
    def diskid(self, value: Optional[int]):
        self.mbr_header.diskid = value

    def prepare(self):
        if self.mbr_header not in self.parts:
            self.parts.append(self.mbr_header)

        # if more than 4 partitions are present, then 4th partition should be extended partition
        # EBR Headers should be added before each logical partition
        partitionCnt = len(list(filter(lambda x: isinstance(x, PartitionRegion), self.parts)))

        if partitionCnt > 4:
            partPtr = 0
            self.parts.sort(key=lambda x: x.start)

            tmpPartList = []
            for part in self.parts:
                if isinstance(part, PartitionRegion):
                    partPtr += 1

                    if partPtr > 3:
                        ebrHeader = EBRHeader()
                        tmpPartList.append(ebrHeader)

                tmpPartList.append(part)

            self.parts = tmpPartList

        super().prepare()

    def create_partition_table(self, filename: Path):
        self._create_partition_table(filename, "msdos")

    def __repr__(self) -> str:
        return "MBR:\n  " + "\n  ".join(map(repr, self.parts))
