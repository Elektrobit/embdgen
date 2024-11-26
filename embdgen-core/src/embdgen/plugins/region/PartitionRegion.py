# SPDX-License-Identifier: GPL-3.0-only

from io import BufferedIOBase

from embdgen.core.utils.class_factory import Config
from embdgen.core.region.BaseContentRegion import BaseContentRegion
from embdgen.core.content import BinaryContent

@Config('content')
@Config('fstype')
class PartitionRegion(BaseContentRegion):
    """Partition region

    This creates an entry in the partition table
    """
    PART_TYPE = 'partition'

    content: BinaryContent
    """Content of this Region"""

    fstype: str
    """
    Filesystem type of this region (e.g. ext4, fat32)
    An EFI system partition for gpt and mbr partition tables can be created with "esp"
    """

    def write(self, out_file: BufferedIOBase):
        out_file.seek(self.start.bytes)
        self.content.write(out_file)
