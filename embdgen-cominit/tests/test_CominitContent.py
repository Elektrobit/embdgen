# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives import serialization, hashes

from embdgen.core.utils.image import get_temp_path
from embdgen.core.utils.SizeType import SizeType
from embdgen.plugins.content.CominitContent import CominitContent
from embdgen.plugins.content.RawContent import RawContent
from embdgen.plugins.content.VerityContent import VerityContent



# Note: only 4096 bytes signature supported, because cominit
# uses exactly 512 bytes from the signature
private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
public_key = private_key.public_key()

invalid_private_key = ec.generate_private_key(ec.SECP256K1())

def verify_signature(metadata: bytes, sig: bytes):
    public_key.verify(sig[:512], metadata + b"\0",
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=hashes.SHA256.digest_size
        ),
        hashes.SHA256()
    )

class TestCominitContent:
    def test_plain(self, tmp_path: Path):
        get_temp_path.TEMP_PATH = tmp_path
        image_file = tmp_path / "image"
        content_file = tmp_path / "content"
        content_file.write_bytes(b"\1" * 4096)
        key_path = tmp_path / "key.pem"
        key_path.write_bytes(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
        obj = CominitContent()
        obj.dm_type = "plain"
        obj.filesystem = "ext4"
        obj.key = key_path

        obj.content = RawContent()
        obj.content.file = content_file

        obj.prepare()

        with image_file.open("wb") as out_file:
            obj.write(out_file)

        assert image_file.stat().st_size == 4096 * 2
        data = image_file.read_bytes()
        assert data[:4096] == b"\1" * 4096

        metadata = data[4096:]
        metadata, sig = metadata.split(b"\0", 1)
        base, verity, crypt = metadata.split(b"\xff", 2)

        assert base.decode() == "1 ext4 rw plain"
        assert verity == b""
        assert crypt == b""

        verify_signature(metadata, sig)


    def test_verity(self, tmp_path):
        get_temp_path.TEMP_PATH = tmp_path
        image_file = tmp_path / "image"
        content_file = tmp_path / "content"
        content_file.write_bytes(b"\1" * 4096 * 2)
        key_path = tmp_path / "key.pem"
        key_path.write_bytes(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
        meta_file = tmp_path / "meta"

        obj = CominitContent()
        obj.dm_type = "verity"
        obj.filesystem = "ext4"
        obj.readonly = True
        obj.key = key_path
        obj.metadata = meta_file

        obj.content = VerityContent()
        obj.content.content = RawContent()
        obj.content.metadata = meta_file
        obj.content.salt = "deadbeef"
        obj.content.hash_block_size = SizeType(512)
        obj.content.content.file = content_file

        obj.prepare()

        with image_file.open("wb") as out_file:
            obj.write(out_file)

        assert image_file.stat().st_size == 4096 * 2 + 512 * 9
        data = image_file.read_bytes()
        assert data[:4096 * 2] == b"\1" * 4096 * 2

        metadata = data[-4096:]
        metadata, sig = metadata.split(b"\0", 1)
        base, verity, crypt = metadata.split(b"\xff", 2)

        assert base.decode() == "1 ext4 ro verity"
        assert verity == b"1 4096 512 2 16 sha256 653ead47527731c0afba60bd7c85f4664bbfd3252d6dca95e39c9d1ec4613fb6 deadbeef"
        assert crypt == b""

        verify_signature(metadata, sig)

    def test_verity_missing_metadata(self, tmp_path: Path):
        obj = CominitContent()
        obj.dm_type = "verity"
        obj.filesystem = "ext4"
        obj.readonly = True
        obj.content = RawContent()
        tmp_file = tmp_path / "file"
        tmp_file.write_bytes(b"")
        obj.content.file = tmp_file

        with pytest.raises(Exception, match="Verity requires a metadata file"):
            obj.prepare()

        obj.metadata = Path("i-do-not-exist")
        with pytest.raises(Exception, match=r"Metadata file .* does not exist"):
            obj.prepare()

        meta_file = tmp_path / "file"
        meta_file.write_text("")
        obj.metadata = meta_file
        with pytest.raises(KeyError):
            obj.prepare()


    def test_verity_writable(self):
        obj = CominitContent()
        obj.dm_type = "verity"
        obj.filesystem = "ext4"
        obj.readonly = False
        obj.metadata = Path()

        with pytest.raises(Exception, match="Verity must be readonly"):
            obj.prepare()

    def test_verity_invalid_bocksizes(self, tmp_path):
        get_temp_path.TEMP_PATH = tmp_path
        image_file = tmp_path / "image"
        content_file = tmp_path / "content"
        content_file.write_bytes(b"\1" * 512 * 2)
        key_path = tmp_path / "key.pem"
        key_path.write_bytes(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
        meta_file = tmp_path / "meta"

        obj = CominitContent()
        obj.dm_type = "verity"
        obj.filesystem = "ext4"
        obj.readonly = True
        obj.key = key_path
        obj.metadata = meta_file

        obj.content = VerityContent()
        obj.content.content = RawContent()
        obj.content.metadata = meta_file
        obj.content.salt = "deadbeef"
        obj.content.data_block_size = SizeType(512)
        obj.content.content.file = content_file

        obj.prepare()

        with image_file.open("wb") as out_file:
            obj.write(out_file)

        data = image_file.read_bytes()
        assert data[4096:4096+65].hex() == "a67ec368305588be6a34bfde7e5a333574316d27eb6f5e2a737e3667fda04591a67ec368305588be6a34bfde7e5a333574316d27eb6f5e2a737e3667fda0459100", "Level 0 of hash table is in correct location"
        assert image_file.stat().st_size == 4096 + 2 * 4096, "Hash table is aligned to hash block size"
        assert image_file.stat().st_size == obj.size.bytes
        assert data[:512 * 2] == b"\1" * 512 * 2

        metadata = data[-4096:]
        metadata, sig = metadata.split(b"\0", 1)
        base, verity, crypt = metadata.split(b"\xff", 2)

        assert base.decode() == "1 ext4 ro verity"
        assert verity == b"1 512 4096 2 1 sha256 b3f20b170c2e942733e9bab7e237b1da46ae0b0698e2087b71cf4b6c7e8ef223 deadbeef"
        assert crypt == b""

    def test_invalid_private_key(self, tmp_path: Path):
        image_file = tmp_path / "image"
        content_file = tmp_path / "content"
        content_file.write_bytes(b"\1" * 512 * 2)
        key_path = tmp_path / "key.pem"
        key_path.write_bytes(invalid_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

        obj = CominitContent()
        obj.dm_type = "plain"
        obj.filesystem = "ext4"
        obj.readonly = True
        obj.key = key_path

        obj.content = RawContent()
        obj.content.file = content_file

        obj.prepare()

        with image_file.open("wb") as out_file:
            with pytest.raises(Exception, match="Only RSA private keys are supported for cominit"):
                obj.write(out_file)
