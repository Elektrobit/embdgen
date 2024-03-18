# SPDX-License-Identifier: GPL-3.0-only

import pytest
from pathlib import Path

from embdgen.core.utils.SizeType import SizeType
from embdgen.core.utils.image import create_empty_image, BuildLocation
from embdgen.plugins.content.RawContent import RawContent
from embdgen.plugins.content.VerityContent import VerityContent


class TestVerityContent():

    @pytest.mark.parametrize(
        "use_internal_implementation, algorithm, salt, data_block_size, hash_block_size, size, expected_hashtable_size, expected_root_hash", [
            (True,  "sha256",   "deadbeef", 4096, 4096, 4096 * 129,  3 * 4096,  "ff81ce250f9277638a39068ca8e007d15f036511c06f94984e90bf2f428f7cad"),
            (False, "sha256",   "deadbeef", 4096, 4096, 4096 * 129,  3 * 4096,  "ff81ce250f9277638a39068ca8e007d15f036511c06f94984e90bf2f428f7cad"),
            (True,  None,       "deadbeef", None, None, 4096 * 129,  3 * 4096,  "ff81ce250f9277638a39068ca8e007d15f036511c06f94984e90bf2f428f7cad"),
            (False, None,       "deadbeef", None, None, 4096 * 129,  3 * 4096,  "ff81ce250f9277638a39068ca8e007d15f036511c06f94984e90bf2f428f7cad"),
            (True,  None,       None,       4096, 4096, 4096 * 129,  3 * 4096,  None),
            (False, None,       None,       4096, 4096, 4096 * 129,  3 * 4096,  None),
            (True,  "sha512",   "deadbeef", 4096, 4096, 4096 * 129,  4 * 4096,  "daca624989895b2f8fb4a012a39226888d2bf5e2b427fd7b79b6cd74e102b0ce3800f20cb1d1d241e454dfb13e8592c30e83e7fb0bafa4e261d46fd4e0a89c0c"),
            (False, "sha512",   "deadbeef", 4096, 4096, 4096 * 129,  4 * 4096,  "daca624989895b2f8fb4a012a39226888d2bf5e2b427fd7b79b6cd74e102b0ce3800f20cb1d1d241e454dfb13e8592c30e83e7fb0bafa4e261d46fd4e0a89c0c"),
            (True,  "sha512",   "deadbeef", 512,  1024, 512 * 1032,  142 * 512, "3b0cbf39bf2d64539782ecbef219b1e9f3e976e81dec1a5c45ba1953a67880244f212fbcfd988c6d7dbbf84bd0875dc3d21769888d4c7bf4c1169045c3291dab"),
            (False, "sha512",   "deadbeef", 512,  1024, 512 * 1032,  142 * 512, "3b0cbf39bf2d64539782ecbef219b1e9f3e976e81dec1a5c45ba1953a67880244f212fbcfd988c6d7dbbf84bd0875dc3d21769888d4c7bf4c1169045c3291dab"),
            (True,  "sha512",   "deadbeef", 1024, 512,  1024 * 516,  77 * 512,  "cbe5ff940b98e704ecb5404a1e97acb6264f37254bb7ede95e5d386e3956866f9670c1afd921ec258031875f3e30179f5797f3002dba87cd5019bea18404da93"),
            (False, "sha512",   "deadbeef", 1024, 512,  1024 * 516,  77 * 512,  "cbe5ff940b98e704ecb5404a1e97acb6264f37254bb7ede95e5d386e3956866f9670c1afd921ec258031875f3e30179f5797f3002dba87cd5019bea18404da93")
        ]
    )
    def test_simple(
        self,
        use_internal_implementation: bool,
        algorithm: str,
        salt: str,
        data_block_size: int,
        hash_block_size: int,
        size: int,
        expected_hashtable_size: int,
        expected_root_hash: str,
        tmp_path: Path
    ):
        BuildLocation().set_path(tmp_path)
        metadata_file = tmp_path / "metadata.txt"
        input_file = tmp_path / "input"
        image_file = tmp_path / "image"

        create_empty_image(input_file, size)

        raw = RawContent()
        raw.file = input_file

        obj = VerityContent()
        obj.metadata = metadata_file
        obj.content = raw
        if algorithm:
            obj.algorithm = algorithm
        if salt:
            obj.salt = salt
        if data_block_size:
            obj.data_block_size = SizeType(data_block_size)
        if hash_block_size:
            obj.hash_block_size = SizeType(hash_block_size)

        obj.use_internal_implementation = use_internal_implementation
        obj.prepare()

        assert metadata_file.exists() and metadata_file.stat().st_size > 200

        # print(metadata_file.read_text())

        if expected_root_hash:
            assert [line.split(":") for line in  metadata_file.read_text().splitlines() if line.startswith("Root hash")][0][1].strip() == expected_root_hash

        verity_file = obj.hash_file

        # 129 Blocks of data are condensed into three block of metadata (2 for level 1 and 1 for level 0)
        assert verity_file.exists() and verity_file.stat().st_size == expected_hashtable_size

        with image_file.open("wb") as f:
            obj.write(f)

        assert image_file.stat().st_size == size + expected_hashtable_size

    def test_not_block_size_aligned(self, tmp_path: Path):
        BuildLocation().set_path(tmp_path)
        input_file = tmp_path / "input"
        create_empty_image(input_file, 4096 * 2 - 1)

        obj = VerityContent()
        obj.content = RawContent()
        obj.content.file = input_file
        obj.metadata = "meta"
        with pytest.raises(Exception, match=r"block size-aligned"):
            obj.prepare()
