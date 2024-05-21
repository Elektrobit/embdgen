# SPDX-License-Identifier: GPL-3.0-only

import io
from pathlib import Path
import zlib
import struct
import math

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
        self.size = SizeType(512)

    def write(self, out_file: io.BufferedIOBase):
        return


class GPTPartitionTable(BaseRegion):

    backup_table_start: SizeType
    # A flag to keep track whether the gpt partition table needs be relocated
    gpt_table_relocated: bool

    def __init__(self, name="GPT Partition Table") -> None:
        super().__init__()
        self.name = name
        self.is_partition = False
        self.start = SizeType(1024)
        self.size = SizeType(512*32)

    def write(self, out_file: io.BufferedIOBase) -> None:
        if self.gpt_table_relocated is True:
            # change the GPT Table address data in GPT Header
            out_file.seek(512 + 72)
            LBAforTable = self.start.sectors
            out_file.write(struct.pack("I", LBAforTable))

            # Recalculate CRC
            # Read Header Size
            out_file.seek(512 + 12)
            header_size = struct.unpack('I', out_file.read(4))[0]

            # Reset old CRC
            out_file.seek(512 + 16)
            out_file.write(struct.pack("I", 0))

            # Read Header and calculate CRC
            out_file.seek(512)
            header_data = out_file.read(header_size)
            crc_header = zlib.crc32(header_data)
            out_file.seek(512 + 16)
            out_file.write(struct.pack("I", crc_header))

            # Copy the GPT Partition table from GPT Backup Table
            out_file.seek(int(self.backup_table_start.bytes))
            gptTableData = out_file.read(512 * 32)
            out_file.seek(self.start.bytes)
            out_file.write(gptTableData)


class GPT(BaseLabel):
    """GUID Partition Table (GPT) partition type"""
    LABEL_TYPE = 'gpt'

    GPT_DISK_ID_OFFSET = 0x238

    pmbr_header: PMBRHeader
    gpt_header: GPTHeader
    gpt_table: GPTPartitionTable
    sgpt_header: GPTHeader


    def __init__(self) -> None:
        super().__init__()
        self.pmbr_header = PMBRHeader()
        self.gpt_header = GPTHeader()
        self.gpt_table = GPTPartitionTable()
        self.sgpt_header = GPTHeader("Secondary GPT Header and Table")
        # Size of secondary header is set to header + table again since splitting secondary header is not necessary
        self.sgpt_header.size = SizeType(512 * 33)
        self.parts.append(self.pmbr_header)
        self.parts.append(self.gpt_header)
        self.parts.append(self.gpt_table)
        self.gpt_table.gpt_table_relocated = False

    def check_for_gpt_relocation (self) -> None:
        i = 0
        while i < len(self.parts):
            if not self.parts[i].start.is_undefined and self.parts[i] != self.gpt_table:
                if self.parts[i].start < self.gpt_table.start + self.gpt_table.size \
                    and self.parts[i].start + self.parts[i].size > self.gpt_table.start:
                    # Locate the GPT Table after this and continue checking
                    sectorsStart = math.ceil((self.parts[i].start + self.parts[i].size).bytes / 512)
                    self.gpt_table.start = SizeType(sectorsStart * 512)
                    self.gpt_table.gpt_table_relocated = True
                    # The loop is restarted each time a collision is found,
                    # in case the addresses in the config are not sorted.
                    i = 0
            i += 1

        if self.gpt_table.gpt_table_relocated is True:
            print("The location for the GPT Partition Table is used by another region. Table will be relocated")


    def prepare(self) -> None:
        if self.pmbr_header not in self.parts:
            self.parts.append(self.pmbr_header)
        if self.gpt_header not in self.parts:
            self.parts.append(self.gpt_header)
        if self.gpt_table not in self.parts:
            self.parts.append(self.gpt_table)
        self.check_for_gpt_relocation()

        super().prepare()
        self.sgpt_header.start = self.parts[-1].start + self.parts[-1].size
        self.parts.append(self.sgpt_header)
        self.gpt_table.backup_table_start = self.sgpt_header.start

    def create_partition_table(self, filename: Path) -> None:
        self._create_partition_table(filename, "gpt")

    def __repr__(self) -> str:
        return "GPT:\n  " + "\n  ".join(map(repr, self.parts))
