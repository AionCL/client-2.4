import importlib.util
import json
import pathlib
import struct
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("package_camera", pathlib.Path(__file__).with_name("package-camera.py"))
package_camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_camera)


class CameraPackageTests(unittest.TestCase):
    def test_append_preserves_base_and_validates_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            base = {"formatVersion": 1, "product": "AionCL", "clientVersion": "2.4.4",
                    "packages": [{"name": "base.zip", "size": 20, "sha256": "a" * 64,
                                  "fileCount": 1, "uncompressedSize": 40, "files": [], "mirrors": ["https://example.test/base.zip"]}]}
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(base))
            helper = root / "helper.exe"
            data = bytearray(128)
            data[:2] = b"MZ"
            struct.pack_into("<I", data, 0x3c, 64)
            data[64:68] = b"PE\0\0"
            struct.pack_into("<H", data, 68, 0x8664)
            helper.write_bytes(data)
            result = package_camera.build(manifest, helper, root / "out", "2.4.5")
            self.assertEqual(result["packages"][:-1], base["packages"])
            self.assertEqual(result["sourceFileCount"], 2)
            self.assertEqual(result["sourceBytes"], 168)
            last = result["packages"][-1]
            with zipfile.ZipFile(root / "out" / last["name"]) as archive:
                self.assertEqual(archive.namelist(), ["tools/AionCL.Camera.exe"])
                self.assertEqual(archive.read(archive.namelist()[0]), data)
            with self.assertRaises(FileExistsError):
                package_camera.build(manifest, helper, root / "out", "2.4.5")
            with self.assertRaises(ValueError):
                package_camera.build(manifest, helper, root / "old", "2.4.4")
            struct.pack_into("<H", data, 68, 0x14c)
            helper.write_bytes(data)
            with self.assertRaises(ValueError):
                package_camera.build(manifest, helper, root / "wrong", "2.4.5")


if __name__ == "__main__":
    unittest.main()
