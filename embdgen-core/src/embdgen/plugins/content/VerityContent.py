# SPDX-License-Identifier: GPL-3.0-only

import subprocess
import io
from io import BufferedIOBase
import math
import random
from pathlib import Path
from typing import Optional

import hashlib

from embdgen.core.utils.class_factory import Config
from embdgen.core.content.BinaryContent import BinaryContent
from embdgen.core.utils.image import copy_sparse, get_temp_file
from embdgen.core.utils.SizeType import SizeType

@Config('content')
@Config('metadata')
@Config('salt', optional=True) # TODO: Maybe add hexstring
@Config('algorithm', optional=True)
@Config('use_internal_implementation', optional=True)
@Config('data_block_size', optional=True)
@Config('hash_block_size', optional=True)
class VerityContent(BinaryContent):
    """dm-verity hashed content
    
    Calculates the hashes for the content and writes them directly after
    the content (block aligned).

    Additionally a metadata file is generated, that contains the all
    values required, to open the verity device. This file can be parsed by
    CominitContent (from embdgen-cominit), to generate cominit metadata.
    """
    CONTENT_TYPE = "verity"

    content: BinaryContent
    """The payload content of the partition"""
    metadata: Path
    """A path to a file, where the metadata is written to.
    
    This is in the same format as the output of veritysetup.
    """

    salt: Optional[str] = None
    """Salt to use for verity hashes. This can be useful, to generate reproducible images"""
    algorithm: str = "sha256"
    """Hash algorithm to use (defaults to sha256)"""
    data_block_size: SizeType = SizeType(4096)
    """Size of data blocks (defaults to 4096)"""
    hash_block_size: SizeType = SizeType(4096)
    """Size of hash blocks (defaults to 4096)"""

    use_internal_implementation: bool = True
    """
    If set to false, veritysetup is used, otherwise a pure python solution is used, to generate the hash tree.
    """

    __padding: int = 0
    __hash_file: Optional[Path] = None

    @property
    def hash_file(self):
        if not self.__hash_file:
            self.__hash_file = get_temp_file(ext=".hash")
        return self.__hash_file

    def _do_verity(self) -> None:
        verity_params = [
            "--no-superblock",
            "--format=1",
            f"--hash={self.algorithm}",
            f"--data-block-size={self.data_block_size.bytes}",
            f"--hash-block-size={self.hash_block_size.bytes}",
        ]

        if self.salt:
            verity_params.append(f"--salt={self.salt}")


        with open(self.metadata, "w", encoding="ascii") as f:
            subprocess.run([
                "veritysetup",
                "format",
                *verity_params,
                self.content.result_file,
                self.hash_file
            ], stdout=f, stderr=f, check=True)

        self.size.bytes = self.content.size.bytes + self.hash_file.stat().st_size

    def _do_verity_py(self): #pylint: disable = too-many-locals
        """
        # Calculating the hash tree is not really hard:
        #
        # 1. Calculate sha256 over all each block (4096 byte by default) and concatenate them.
        # 2. Extend the result with zeroes to align to a block
        # 3. If the result is bigger than one block, do it again with the previously calculate blocks
        #    and prepend the result, until it fits in one block
        # 4. Calculate the sha256 hash of that last block -> this is the root hash
        """
        data_blocksize = self.data_block_size.bytes
        hash_blocksize = self.hash_block_size.bytes
        salt = bytearray.fromhex(self.salt) if self.salt else random.randbytes(32)
        hasher = hashlib.new(self.algorithm, salt, usedforsecurity=False)
        hash_len = hasher.digest_size

        def get_hash_block_count(num_blocks: int) -> int:
            return math.ceil(num_blocks * hash_len / hash_blocksize)

        num_data_blocks = math.floor(self.content.size.bytes / data_blocksize)

        block_counts = []
        num_blocks = num_data_blocks
        while num_blocks != 1:
            num_blocks = get_hash_block_count(num_blocks)
            block_counts.append(num_blocks)
        total_hash_blocks = sum(block_counts)

        level_start_block = []
        start = 0
        for block in reversed(block_counts):
            level_start_block.append(start)
            start += block
        level_start_block.reverse()

        self.size.bytes = self.content.size.bytes + self.__padding + total_hash_blocks *  hash_blocksize

        cur_level = 0
        with open(self.hash_file, "wb") as out_file:
            out_file.truncate((level_start_block[0] + block_counts[0]) * hash_blocksize)
            # Start with data blocks:
            out_file.seek(level_start_block[cur_level] * hash_blocksize)
            with self.content.result_file.open("rb") as in_file:
                for _ in range(num_data_blocks):
                    lhasher = hasher.copy()
                    lhasher.update(in_file.read(data_blocksize))
                    out_file.write(lhasher.digest())
            cur_level += 1
            # Now condense levels
            while cur_level < len(level_start_block):
                out_file.flush()
                out_file.seek(level_start_block[cur_level] * hash_blocksize)
                with open(self.hash_file, "rb") as in_file:
                    in_file.seek(level_start_block[cur_level - 1] * hash_blocksize)
                    for _ in range(block_counts[cur_level - 1]):
                        lhasher = hasher.copy()
                        lhasher.update(in_file.read(hash_blocksize))
                        out_file.write(lhasher.digest())
                cur_level += 1

        # Calculate root hash
        with open(self.hash_file, "rb") as in_file:
            hasher.update(in_file.read(hash_blocksize))
            root_hash = hasher.hexdigest()

        with open(self.metadata, "w", encoding="ascii") as f:
            f.write(f"""
UUID:
Hash type:              1
Data blocks:            {num_data_blocks}
Data block size:        {data_blocksize}
Hash block size:        {hash_blocksize}
Hash algorithm:         {self.algorithm}
Salt:                   {salt.hex()}
Root hash:              {root_hash}
""")

    def prepare(self) -> None:
        self.content.prepare()

        if self.content.size.bytes % self.data_block_size.bytes != 0:
            raise Exception("Underlying data device must be block size-aligned")

        if self.use_internal_implementation:
            self._do_verity_py()
        else:
            self._do_verity()

        self.__padding = math.ceil(
                self.content.size.bytes / self.hash_block_size.bytes
            ) * self.hash_block_size.bytes - self.content.size.bytes
        self.size.bytes += self.__padding


    def do_write(self, file: BufferedIOBase):
        self.content.write(file)
        file.seek(self.__padding, io.SEEK_CUR)
        with open(self.hash_file, "rb") as in_file:
            copy_sparse(file, in_file)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.content})"
