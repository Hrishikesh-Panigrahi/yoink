"""Pytest config: put `src/` on sys.path so flat imports work."""

import os
import sys

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import libtorrent as lt  # noqa: E402  (must follow the sys.path setup above)

DEFAULT_PIECE_LENGTH = 1024 * 1024


class FakeFileStorage:
    """The subset of `lt.file_storage` the streaming code reads."""

    def __init__(self, files):
        self._files = []
        offset = 0
        for path, size in files:
            self._files.append((path, int(size), offset))
            offset += int(size)

    def num_files(self):
        return len(self._files)

    def file_path(self, index):
        return self._files[index][0]

    def file_size(self, index):
        return self._files[index][1]

    def file_offset(self, index):
        return self._files[index][2]

    @property
    def total_size(self):
        return sum(entry[1] for entry in self._files)


class FakeTorrentInfo:
    def __init__(self, files, piece_length):
        self._files = FakeFileStorage(files)
        self._piece_length = piece_length

    def files(self):
        return self._files

    def piece_length(self):
        return self._piece_length

    def num_pieces(self):
        total = self._files.total_size
        return max(1, -(-total // self._piece_length))


class FakeStatus:
    def __init__(self, save_path):
        self.save_path = save_path


class FakeTorrentHandle:
    """A stand-in for `lt.torrent_handle` covering what streaming.py calls.

    Records the deadlines and flag changes it is given so tests can assert on
    the order pieces were asked for.
    """

    def __init__(
        self,
        files,
        piece_length=DEFAULT_PIECE_LENGTH,
        save_path="C:/downloads",
        have=(),
        metadata=True,
        valid=True,
        priorities=None,
    ):
        self._info = FakeTorrentInfo(files, piece_length)
        self._save_path = save_path
        self._have = set(have)
        self._metadata = metadata
        self._valid = valid
        self._priorities = list(priorities) if priorities else [4] * len(files)
        self.flags_value = 0
        self.deadlines = []
        self.clear_calls = 0

    # --- libtorrent surface ---

    def is_valid(self):
        return self._valid

    def has_metadata(self):
        return self._metadata

    def get_torrent_info(self):
        return self._info

    def status(self):
        return FakeStatus(self._save_path)

    def set_flags(self, flags):
        self.flags_value |= int(flags)

    def unset_flags(self, flags):
        self.flags_value &= ~int(flags)

    def flags(self):
        return self.flags_value

    def file_priority(self, index, priority=None):
        if priority is None:
            return self._priorities[index]
        self._priorities[index] = priority
        return priority

    def set_piece_deadline(self, piece, deadline_ms):
        self.deadlines.append((piece, deadline_ms))

    def clear_piece_deadlines(self):
        self.clear_calls += 1
        self.deadlines.clear()

    def have_piece(self, piece):
        return piece in self._have

    # --- test helpers ---

    @property
    def priorities(self):
        return list(self._priorities)

    @property
    def is_sequential(self):
        return bool(self.flags_value & int(lt.torrent_flags.sequential_download))

    def mark_have(self, pieces):
        self._have.update(pieces)
