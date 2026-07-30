from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from robot_pet.checksums import checksum_lines, parse_checksums, sha256_file, write_checksums


class ChecksumTests(unittest.TestCase):
    def test_write_parse_and_sort(self) -> None:
        with tempfile.TemporaryDirectory(prefix="robot-checksum-test-") as temporary:
            root = Path(temporary)
            (root / "b.txt").write_text("b", encoding="utf-8")
            (root / "a.txt").write_text("a", encoding="utf-8")
            lines = checksum_lines(root, [Path("b.txt"), Path("a.txt")])
            self.assertTrue(lines[0].endswith("  a.txt"))
            output = root / "checksums.txt"
            write_checksums(root, [Path("b.txt"), Path("a.txt")], output)
            parsed = parse_checksums(output)
            self.assertEqual([path.as_posix() for _, path in parsed], ["a.txt", "b.txt"])
            self.assertEqual(parsed[0][0], sha256_file(root / "a.txt"))

    def test_invalid_and_unsafe_lines_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="robot-checksum-test-") as temporary:
            path = Path(temporary) / "checksums.txt"
            path.write_text("bad\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid checksum line"):
                parse_checksums(path)
            path.write_text(f"{'0' * 64}  ../escape\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe checksum path"):
                parse_checksums(path)

    def test_comments_and_blank_lines_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="robot-checksum-test-") as temporary:
            path = Path(temporary) / "checksums.txt"
            path.write_text("\n# generated\n", encoding="utf-8")
            self.assertEqual(parse_checksums(path), [])


if __name__ == "__main__":
    unittest.main()
