import re
from typing import List
from dataclasses import dataclass
import subprocess

@dataclass
class FdiskRegion:
    TYPE_FAT32_LBA = 0x0C
    TYPE_LINUX_NATIVE = 0x83
    TYPE_EXTENDED = 0x05
    TYPE_EFS = 0xEF

    start_sector: int
    end_sector: int
    sectors: int
    type_id: int
    boot: bool


class FdiskParser:
    is_valid: bool = False
    label_type: str = None
    diskid: int = None
    regions: List[FdiskRegion]

    def __init__(self, image):
        self.regions = []
        ret = subprocess.run([
            'fdisk',
            '-l',
            image
        ], stdout=subprocess.PIPE, check=False, encoding="ascii")
        if ret.returncode == 0:
            self.is_valid = True
        self._parse(ret.stdout)

    def _parse(self, output: str):
        """
        Disk image: 5,1 MiB, 5250560 bytes, 10255 sectors
        Units: sectors of 1 * 512 = 512 bytes
        Sector size (logical/physical): 512 bytes / 512 bytes
        I/O size (minimum/optimal): 512 bytes / 512 bytes
        Disklabel type: dos
        Disk identifier: 0x5a30abff

        Device       Boot Start   End Sectors Size Id Type
        image1 *       13    14       2   1K 83 Linux
        image2         15 10254   10240   5M  b W95 FAT32

        
        Disk /image: 100,3 MiB, 104891904 bytes, 204867 sectors
        Units: sectors of 1 * 512 = 512 bytes
        Sector size (logical/physical): 512 bytes / 512 bytes
        I/O size (minimum/optimal): 512 bytes / 512 bytes
        Disklabel type: gpt
        Disk identifier: 9F781A13-49F0-4436-A1DA-845216AADF83

        Device Start    End Sectors  Size Type
        image1    34 204833  204800  100M EFI System

        """
        in_regions = False
        for line in output.splitlines():
            if in_regions:
                parts = re.split(r"\s+", line)
                if not parts[1] == "*":
                    parts.insert(1, "")
                _, boot, start, end, sectors, _, type_id, *type_id_ext = parts
                if self.label_type == "dos":
                    type_id = int(type_id, 16)
                elif self.label_type == "gpt":
                    type_id = " ".join([type_id, *type_id_ext]).lower()
                    if type_id == "efi system":
                        type_id = FdiskRegion.TYPE_EFS
                    elif type_id == "microsoft basic data":
                        type_id = FdiskRegion.TYPE_FAT32_LBA
                    else:
                        raise Exception(f"Unimplemented partition type for gpt: {type_id}")
                else:
                    raise Exception(f"Unexpected label type in fdisk output: {self.label_type}")

                self.regions.append(FdiskRegion(
                    int(start),
                    int(end),
                    int(sectors),
                    type_id,
                    boot == "*"
                ))

            else:
                if line.startswith("Disklabel type:"):
                    self.label_type  = line.split(":")[1].strip()
                if line.startswith("Disk identifier:"):
                    self.diskid = line.split(":")[1].strip()
                elif line.startswith("Device"):
                    in_regions = True

    def __repr__(self) -> str:
        out = []
        for i, r in enumerate(self.regions):
            out.append(f"{i} {r.start_sector:>5} - {r.start_sector + r.sectors:>5} ({r.sectors:>4} Sectors), {r.type_id}")
        return "\n".join(out)
