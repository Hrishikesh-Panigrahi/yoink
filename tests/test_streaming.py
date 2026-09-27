from __future__ import annotations

import libtorrent as lt
import pytest

from conftest import DEFAULT_PIECE_LENGTH, FakeTorrentHandle
from torrents import streaming
from torrents.session import Session

MB = 1024 * 1024


def make_session(handles=None) -> Session:
    """A Session with no libtorrent behind it. Streaming only uses its dicts."""
    return Session(lt_session=None, save_path="C:/downloads", handles=handles or {})


# Picking the file


@pytest.mark.parametrize(
    "path, expected",
    [
        ("Movie.mkv", True),
        ("Movie.MP4", True),
        ("clip.webm", True),
        ("readme.txt", False),
        ("Movie.mkv.torrent", False),
        ("no-extension", False),
    ],
)
def test_is_video(path, expected):
    assert streaming.is_video(path) is expected


def test_pick_video_file_takes_the_largest():
    files = [("Extras.mkv", 200 * MB), ("Movie.mkv", 4000 * MB), ("readme.txt", 900)]

    assert streaming.pick_video_file(files) == 1


def test_pick_video_file_ignores_a_sample_folder():
    files = [("Sample/movie-sample.mkv", 900 * MB), ("Movie.mkv", 400 * MB)]

    assert streaming.pick_video_file(files) == 1


def test_pick_video_file_ignores_a_sample_prefixed_name():
    files = [("sample-movie.mkv", 900 * MB), ("Movie.mkv", 400 * MB)]

    assert streaming.pick_video_file(files) == 1


def test_pick_video_file_falls_back_to_a_sample_when_that_is_all_there_is():
    files = [("readme.txt", 900), ("Sample/clip.mkv", 40 * MB)]

    assert streaming.pick_video_file(files) == 1


def test_pick_video_file_returns_none_without_video():
    assert streaming.pick_video_file([("readme.txt", 900), ("cover.jpg", 40)]) is None
    assert streaming.pick_video_file([]) is None


# Piece arithmetic


def test_plan_covers_both_ends_of_the_file():
    plan = streaming.plan_stream(
        file_offset=0, file_size=1000 * MB, piece_length=MB, num_pieces=1000
    )

    assert plan.first_piece == 0
    assert plan.last_piece == 999
    # 16 MB of head is 16 pieces, plus one because the file may not start on a
    # piece boundary.
    assert plan.head_pieces == tuple(range(0, 17))
    assert plan.tail_pieces == (997, 998, 999)


def test_plan_offsets_a_file_that_starts_mid_torrent():
    plan = streaming.plan_stream(
        file_offset=100 * MB, file_size=50 * MB, piece_length=MB, num_pieces=1000
    )

    assert plan.first_piece == 100
    assert plan.last_piece == 149
    assert plan.head_pieces[0] == 100
    assert plan.tail_pieces[-1] == 149


def test_plan_handles_a_file_that_does_not_start_on_a_piece_boundary():
    # Half a piece in, so the first byte of the file lives in piece 10.
    plan = streaming.plan_stream(
        file_offset=10 * MB + MB // 2, file_size=4 * MB, piece_length=MB, num_pieces=100
    )

    assert plan.first_piece == 10
    assert plan.last_piece == 14  # the last byte spills into piece 14


def test_plan_never_overlaps_head_and_tail_on_a_small_file():
    plan = streaming.plan_stream(
        file_offset=0, file_size=4 * MB, piece_length=MB, num_pieces=100
    )

    # The whole file fits inside the head window, so there is no separate tail.
    assert plan.head_pieces == (0, 1, 2, 3)
    assert plan.tail_pieces == ()
    assert set(plan.head_pieces) & set(plan.tail_pieces) == set()


def test_plan_clamps_to_the_torrents_last_piece():
    plan = streaming.plan_stream(
        file_offset=0, file_size=1000 * MB, piece_length=MB, num_pieces=10
    )

    assert plan.last_piece == 9
    assert max(plan.head_pieces) <= 9
    assert all(piece <= 9 for piece in plan.tail_pieces)


def test_plan_survives_a_zero_length_file():
    plan = streaming.plan_stream(file_offset=0, file_size=0, piece_length=MB, num_pieces=10)

    assert plan.head_pieces == (0,)
    assert plan.tail_pieces == ()


def test_plan_rejects_a_nonsense_layout():
    with pytest.raises(ValueError):
        streaming.plan_stream(file_offset=0, file_size=MB, piece_length=0, num_pieces=10)
    with pytest.raises(ValueError):
        streaming.plan_stream(file_offset=0, file_size=MB, piece_length=MB, num_pieces=0)



# start_stream


def test_start_stream_switches_to_sequential_and_rushes_the_head():
    handle = FakeTorrentHandle([("readme.txt", 1024), ("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})

    status = streaming.start_stream(session, "ABC")

    assert status is not None
    assert status.file_index == 1
    assert handle.is_sequential
    assert session.streams == {"abc": 1}

    # Head pieces are asked for in playback order, with rising deadlines.
    head_deadlines = handle.deadlines[: status.head_total]
    assert [piece for piece, _ in head_deadlines] == sorted(p for p, _ in head_deadlines)
    assert [ms for _, ms in head_deadlines] == sorted(ms for _, ms in head_deadlines)
    assert head_deadlines[0][1] == 0


def test_start_stream_asks_for_the_tail_after_the_head():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})

    status = streaming.start_stream(session, "abc")

    head = handle.deadlines[: status.head_total]
    tail = handle.deadlines[status.head_total :]
    assert len(tail) == status.tail_total
    assert min(ms for _, ms in tail) > max(ms for _, ms in head)
    assert max(piece for piece, _ in tail) == status.last_piece


def test_start_stream_reports_the_path_on_disk():
    handle = FakeTorrentHandle([("Show/Ep1.mkv", 500 * MB)], save_path="C:/downloads/Show")
    session = make_session({"abc": handle})

    status = streaming.start_stream(session, "abc")

    assert status.path == "Show/Ep1.mkv"
    assert status.absolute_path.replace("\\", "/") == "C:/downloads/Show/Show/Ep1.mkv"


def test_start_stream_unskips_the_target_file():
    handle = FakeTorrentHandle(
        [("readme.txt", 1024), ("Movie.mkv", 500 * MB)], priorities=[4, 0]
    )
    session = make_session({"abc": handle})

    streaming.start_stream(session, "abc")

    assert handle.priorities[1] == 4


def test_start_stream_leaves_other_files_priorities_alone():
    handle = FakeTorrentHandle(
        [("Extra.mkv", 10 * MB), ("Movie.mkv", 500 * MB)], priorities=[0, 4]
    )
    session = make_session({"abc": handle})

    streaming.start_stream(session, "abc")

    assert handle.priorities[0] == 0


def test_start_stream_honours_an_explicit_file_index():
    handle = FakeTorrentHandle([("Extra.mkv", 10 * MB), ("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})

    status = streaming.start_stream(session, "abc", file_index=0)

    assert status.file_index == 0


def test_start_stream_falls_back_when_the_index_is_out_of_range():
    handle = FakeTorrentHandle([("Extra.mkv", 10 * MB), ("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})

    status = streaming.start_stream(session, "abc", file_index=99)

    assert status.file_index == 1


def test_start_stream_returns_none_without_metadata():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)], metadata=False)
    session = make_session({"abc": handle})

    assert streaming.start_stream(session, "abc") is None
    assert session.streams == {}


def test_start_stream_returns_none_for_an_invalid_handle():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)], valid=False)
    session = make_session({"abc": handle})

    assert streaming.start_stream(session, "abc") is None


def test_start_stream_returns_none_for_an_unknown_hash():
    assert streaming.start_stream(make_session(), "nope") is None


def test_start_stream_returns_none_when_nothing_is_playable():
    handle = FakeTorrentHandle([("readme.txt", 1024), ("cover.jpg", 40)])
    session = make_session({"abc": handle})

    assert streaming.start_stream(session, "abc") is None
    assert session.streams == {}


# stream_status


def test_status_is_not_ready_with_an_empty_buffer():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})

    status = streaming.start_stream(session, "abc")

    assert status.head_have == 0
    assert status.ready is False
    assert status.to_dict()["bufferProgress"] == 0.0


def test_status_becomes_ready_once_both_ends_are_in():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})
    plan_status = streaming.start_stream(session, "abc")
    plan = streaming.plan_stream(0, 500 * MB, DEFAULT_PIECE_LENGTH, handle.get_torrent_info().num_pieces())

    handle.mark_have(plan.head_pieces)
    partway = streaming.stream_status(session, "abc")
    assert partway.head_have == plan_status.head_total
    assert partway.ready is False  # the tail is still missing

    handle.mark_have(plan.tail_pieces)
    done = streaming.stream_status(session, "abc")
    assert done.ready is True
    assert done.to_dict()["bufferProgress"] == 100.0


def test_status_reports_the_sequential_flag():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})

    streaming.start_stream(session, "abc")
    assert streaming.stream_status(session, "abc").sequential is True


def test_status_is_none_when_not_streaming():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})

    assert streaming.stream_status(session, "abc") is None


def test_status_is_none_after_the_handle_goes_away():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})
    streaming.start_stream(session, "abc")

    session.handles.pop("abc")

    assert streaming.stream_status(session, "abc") is None


def test_status_dict_is_camel_case_for_the_web_ui():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})

    payload = streaming.start_stream(session, "abc").to_dict()

    assert set(payload) == {
        "hash", "fileIndex", "path", "absolutePath", "size", "firstPiece",
        "lastPiece", "headHave", "headTotal", "tailHave", "tailTotal",
        "bufferProgress", "sequential", "ready",
    }


# stop_stream


def test_stop_stream_clears_deadlines_and_leaves_sequential_mode():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})
    streaming.start_stream(session, "abc")

    assert streaming.stop_stream(session, "ABC") is True
    assert handle.clear_calls == 1
    assert handle.is_sequential is False
    assert session.streams == {}


def test_stop_stream_reports_false_when_nothing_was_streaming():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})

    assert streaming.stop_stream(session, "abc") is False


def test_stop_stream_still_forgets_a_torrent_whose_handle_is_gone():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    session = make_session({"abc": handle})
    streaming.start_stream(session, "abc")
    session.handles.pop("abc")

    assert streaming.stop_stream(session, "abc") is True
    assert session.streams == {}


def test_stop_stream_leaves_other_torrent_flags_untouched():
    handle = FakeTorrentHandle([("Movie.mkv", 500 * MB)])
    handle.set_flags(lt.torrent_flags.auto_managed)
    session = make_session({"abc": handle})
    streaming.start_stream(session, "abc")

    streaming.stop_stream(session, "abc")

    assert handle.flags_value & int(lt.torrent_flags.auto_managed)
