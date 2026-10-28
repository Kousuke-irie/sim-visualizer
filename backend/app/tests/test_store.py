import pytest

from app.config import SESSION_TTL_SECONDS
from app.parsers.dat_parser import parse_dat_text
from app.parsers.plt_parser import parse_plt_text
from app.services.store import Store
from app.tests.sample_data import DX, Z_LEVELS, make_dat_text, make_plt_text, temp_value


def test_plt_meta_has_axis_coords_and_ranges_without_missing():
    meta = Store().add_plt(parse_plt_text(make_plt_text(4, 5, 3)))

    assert meta.dims.model_dump() == {"I": 4, "J": 5, "K": 3}
    assert meta.coords.X == [i * DX for i in range(4)]
    assert meta.coords.Y == [j * DX for j in range(5)]
    assert meta.coords.Z == Z_LEVELS[:3]
    # -999 の陸地は value_ranges に含めない
    assert meta.value_ranges["TEMP"] == pytest.approx([temp_value(1, 0, 0), temp_value(3, 4, 2)])


def test_entries_are_typed_by_kind():
    store = Store()
    plt_id = store.add_plt(parse_plt_text(make_plt_text())).file_id
    dat_id = store.add_dat("DIC", parse_dat_text(make_dat_text())).file_id

    assert store.get_entry(plt_id).variables[0] == "X"
    assert store.get_dat_entry(dat_id).variable == "DIC"
    with pytest.raises(KeyError):
        store.get_entry(dat_id)
    with pytest.raises(KeyError):
        store.get_dat_entry(plt_id)


def test_delete_removes_entry():
    store = Store()
    file_id = store.add_plt(parse_plt_text(make_plt_text())).file_id
    store.delete(file_id)
    with pytest.raises(KeyError):
        store.get_meta(file_id)


def test_expired_entries_are_dropped():
    now = [0.0]
    store = Store(clock=lambda: now[0])
    old_id = store.add_plt(parse_plt_text(make_plt_text())).file_id

    now[0] += SESSION_TTL_SECONDS + 1

    with pytest.raises(KeyError):
        store.get_meta(old_id)
