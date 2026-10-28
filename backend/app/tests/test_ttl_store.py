import pytest

from app.services.ttl_store import TTLStore


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def test_add_returns_unique_ids_and_get_returns_value(clock):
    store: TTLStore[str] = TTLStore(ttl_seconds=10, clock=clock)
    a, b = store.add("a"), store.add("b")
    assert a != b
    assert (store.get(a), store.get(b)) == ("a", "b")


def test_unknown_id_raises_key_error(clock):
    with pytest.raises(KeyError):
        TTLStore(ttl_seconds=10, clock=clock).get("nope")


def test_entry_expires_after_ttl_since_last_access(clock):
    store: TTLStore[str] = TTLStore(ttl_seconds=10, clock=clock)
    old = store.add("old")
    clock.now += 11
    store.add("new")  # 追加時に期限切れを掃除する
    with pytest.raises(KeyError):
        store.get(old)


def test_access_extends_lifetime(clock):
    store: TTLStore[str] = TTLStore(ttl_seconds=10, clock=clock)
    entry_id = store.add("x")
    clock.now += 8
    store.get(entry_id)  # 最終アクセスを更新
    clock.now += 8
    store.add("y")
    assert store.get(entry_id) == "x"


def test_expired_entry_is_rejected_even_before_next_add(clock):
    # 以前は add 時にしか掃除しなかったため、期限切れでも次の add までは取得できた
    store: TTLStore[str] = TTLStore(ttl_seconds=10, clock=clock)
    entry_id = store.add("x")
    clock.now += 11
    with pytest.raises(KeyError):
        store.get(entry_id)


def test_on_expire_is_called_with_id_and_value(clock):
    expired: list[tuple[str, str]] = []
    store: TTLStore[str] = TTLStore(ttl_seconds=10, clock=clock, on_expire=lambda i, v: expired.append((i, v)))
    entry_id = store.add("x")
    clock.now += 11
    store.add("y")
    assert expired == [(entry_id, "x")]


def test_delete(clock):
    store: TTLStore[str] = TTLStore(ttl_seconds=10, clock=clock)
    entry_id = store.add("x")
    store.delete(entry_id)
    store.delete("never-existed")  # 存在しない id でもエラーにしない
    with pytest.raises(KeyError):
        store.get(entry_id)
