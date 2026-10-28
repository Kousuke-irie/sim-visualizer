import os

import pytest

from app.config import DATA_ROOTS_ENV
from app.services.path_policy import PathNotAllowedError, is_data_root, resolve_within_data_roots


def test_path_inside_root_is_resolved(data_root):
    (data_root / "sim").mkdir()
    assert resolve_within_data_roots(str(data_root / "sim")) == os.path.realpath(data_root / "sim")


def test_root_itself_is_allowed(data_root):
    assert resolve_within_data_roots(str(data_root)) == os.path.realpath(data_root)
    assert is_data_root(str(data_root))
    assert not is_data_root(str(data_root / "sim"))


@pytest.mark.parametrize("relative", ["..", "../..", "sim/../../etc"])
def test_dotdot_escaping_root_is_rejected(data_root, relative):
    with pytest.raises(PathNotAllowedError):
        resolve_within_data_roots(os.path.join(str(data_root), relative))


def test_sibling_with_common_prefix_is_rejected(tmp_path, monkeypatch):
    # 文字列の前方一致だと /data が /data2 を許してしまう。パス要素単位で判定していることの確認
    (tmp_path / "data").mkdir()
    (tmp_path / "data2").mkdir()
    monkeypatch.setenv(DATA_ROOTS_ENV, str(tmp_path / "data"))
    with pytest.raises(PathNotAllowedError):
        resolve_within_data_roots(str(tmp_path / "data2"))


def test_symlink_pointing_outside_is_rejected(tmp_path, monkeypatch):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "link").symlink_to(outside)
    monkeypatch.setenv(DATA_ROOTS_ENV, str(root))
    with pytest.raises(PathNotAllowedError):
        resolve_within_data_roots(str(root / "link"))


def test_multiple_roots_separated_by_pathsep(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    monkeypatch.setenv(DATA_ROOTS_ENV, os.pathsep.join([str(a), str(b)]))
    assert resolve_within_data_roots(str(b)) == os.path.realpath(b)
