import pytest

from app.services import plt_cache as plt_cache_module
from app.services.plt_cache import PltCache
from app.tests.sample_data import make_plt_text


@pytest.fixture
def frames(tmp_path):
    paths = []
    for t in range(4):
        path = tmp_path / f"tec-{t:05d}.plt"
        path.write_text(make_plt_text(t=t))
        paths.append(str(path))
    return paths


@pytest.fixture
def parse_counter(monkeypatch):
    calls = []
    original = plt_cache_module.parse_plt_bytes

    def counting(content):
        calls.append(content)
        return original(content)

    monkeypatch.setattr(plt_cache_module, "parse_plt_bytes", counting)
    return calls


def test_second_access_is_served_from_cache(frames, parse_counter):
    cache = PltCache(capacity=2)
    first = cache.get_or_parse("d", 0, frames[0])
    second = cache.get_or_parse("d", 0, frames[0])
    assert first is second
    assert len(parse_counter) == 1


def test_least_recently_used_frame_is_evicted(frames, parse_counter):
    cache = PltCache(capacity=2)
    cache.get_or_parse("d", 0, frames[0])
    cache.get_or_parse("d", 1, frames[1])
    cache.get_or_parse("d", 0, frames[0])  # 0 を最新にする → 1 が最古
    cache.get_or_parse("d", 2, frames[2])  # 容量超過で 1 が追い出される

    cache.get_or_parse("d", 0, frames[0])
    assert len(parse_counter) == 3
    cache.get_or_parse("d", 1, frames[1])
    assert len(parse_counter) == 4


def test_same_frame_index_in_different_dirs_is_not_shared(frames, parse_counter):
    cache = PltCache(capacity=4)
    cache.get_or_parse("a", 0, frames[0])
    cache.get_or_parse("b", 0, frames[1])
    assert len(parse_counter) == 2


def test_invalidate_dir_drops_only_that_dir(frames, parse_counter):
    cache = PltCache(capacity=4)
    cache.get_or_parse("a", 0, frames[0])
    cache.get_or_parse("b", 0, frames[0])
    cache.invalidate_dir("a")

    cache.get_or_parse("b", 0, frames[0])
    assert len(parse_counter) == 2
    cache.get_or_parse("a", 0, frames[0])
    assert len(parse_counter) == 3
