# SPDX-License-Identifier: GPL-3.0-only

import abc
from typing import List, Optional
from pathlib import Path
import parted # type: ignore
from typing_extensions import TypeGuard

from embdgen.plugins.region.PartitionRegion import PartitionRegion

from embdgen.core.utils.SizeType import SizeType
from embdgen.core.utils.image import create_empty_image
from ..utils.class_factory import Config
from ..region import BaseRegion

# pyparted built against libparted 3.4 has a bug and does not export PARTITION_ESP
# If pyparted is built against libparted 3.5.28, it should be defined
# See https://github.com/bcl/parted/commit/aa690ee275db86d1edb2468bcf31c3d7cf81228e
if not hasattr(parted, "PARTITION_ESP"):
    parted.PARTITION_ESP = 18

class PartedInterface:
    """
    Contextmanager interface to parted label creation.

    When used as a context manager, the class will automatically
    commit the changes to the disk.
    """

    _device: parted.Device
    _disk: parted.Disk
    _label_type: str

    def __init__(self, filename: Path, label_type: str) -> None:
        self._label_type = label_type
        self._device = parted.getDevice(filename.as_posix())
        self._disk = parted.freshDisk(self._device, label_type)

    def __enter__(self) -> "PartedInterface":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._disk.commit()

    def add_extended_partition(self, start: int, length: int):
        """Create an extended partition"""
        geometry = parted.Geometry(self._device, start=start, length=length)
        partition = parted.Partition(
            disk=self._disk,
            type=parted.PARTITION_EXTENDED,
            geometry=geometry
        )
        self._disk.addPartition(partition=partition, constraint=parted.Constraint(exactGeom=geometry))

    def add_partition(self, part: PartitionRegion, logical: bool=False, boot_partition: bool=False):
        """Create a normal logical partition"""
        geometry = parted.Geometry(self._device, start=part.start.sectors, length=part.size.sectors)
        partition = parted.Partition(
            disk=self._disk,
            type=parted.PARTITION_LOGICAL if logical else parted.PARTITION_NORMAL,
            geometry=geometry,
            fs=parted.FileSystem(part.fstype == "esp" and "fat32" or part.fstype, geometry=geometry)
        )
        if boot_partition:
            partition.setFlag(parted.PARTITION_BOOT)
        if self._label_type == "msdos":
            partition.setFlag(parted.PARTITION_LBA)
        if part.fstype == "esp":
            partition.setFlag(parted.PARTITION_ESP)
        self._disk.addPartition(partition=partition, constraint=parted.Constraint(exactGeom=geometry))

@Config('parts')
@Config('boot_partition', optional=True)
class BaseLabel(abc.ABC):
    """Base class for labels (i.e. partition types, e.g. MBR or GPT)"""

    parts: List[BaseRegion]
    """List of regions to be included in the image"""

    boot_partition: Optional[str] = None
    """Name of the partitions marked as 'bootable'"""

    def __init__(self) -> None:
        self.parts = []

    def prepare(self) -> None:
        for part in self.parts:
            part.prepare()
        self.parts.sort(key=lambda x: x.start)
        cur_offset = SizeType(0)
        for part in self.parts:
            if part.start.is_undefined:
                part.start = cur_offset
            cur_offset = part.start + part.size

        self._validate_parts()

    def _validate_parts(self) -> None:
        self.parts.sort(key=lambda x: x.start)
        cur_offset = SizeType(0)
        last_part = None
        for part in self.parts:
            if part.start < cur_offset:
                raise Exception(f"Part '{part.name}' overlapps with '{last_part.name}'") # type: ignore[attr-defined]
            last_part = part
            cur_offset += part.size

    def _create_partition_table(self, filename: Path, ptType: str) -> None:
        with PartedInterface(filename, ptType) as pInt:

            def is_partition(x: BaseRegion) -> TypeGuard[PartitionRegion]:
                return isinstance(x, PartitionRegion)

            partitions = list(filter(is_partition, self.parts))
            need_extended = ptType == "msdos" and len(partitions) > 4

            for partIndex, part in enumerate(partitions):
                if need_extended and partIndex == 3:
                    # In the extended Partition Size, + 1 is added to include the size of the first EBR Header
                    pInt.add_extended_partition(
                        part.start.sectors - 1,
                        self.parts[-1].start.sectors + self.parts[-1].size.sectors - part.start.sectors + 1
                    )

                pInt.add_partition(
                    part,
                    need_extended and partIndex >= 3,
                    boot_partition=part.name == self.boot_partition
                )

    def create(self, filename: Path) -> None:
        size = self.parts[-1].start + self.parts[-1].size
        create_empty_image(filename, size.bytes)

        self.create_partition_table(filename)

        with filename.open("rb+") as f:
            for part in self.parts:
                part.write(f)

    @abc.abstractmethod
    def create_partition_table(self, filename: Path) -> None:
        pass
