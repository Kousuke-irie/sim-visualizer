"""アップロード済みデータのインメモリ管理。

パース済みの NumPy 配列をプロセス内メモリに保持し、パラメータ変更のたびに
再パースせず抽出・描画のみ行う。TTLを過ぎたエントリはアクセス時に破棄する。
"""

import time
import uuid
from dataclasses import dataclass, field

import numpy as np

from app.config import MISSING_VALUE, SESSION_TTL_SECONDS
from app.models.common import Coords, DatGrid, DatMeta, Dims, PltMeta
from app.parsers.dat_parser import ParsedDat
from app.parsers.plt_parser import ParsedPlt


@dataclass
class PltEntry:
    variables: list[str]
    dims: dict[str, int]
    grid: np.ndarray  # shape (K, J, I, nvar)
    last_access: float = field(default_factory=time.time)


@dataclass
class DatEntry:
    variable: str
    grid: dict[str, float]  # {"i": .., "j": .., "n": .., "h": ..}
    depths: list[str]
    depth_values: list[float]
    times: np.ndarray  # shape (n_times,)
    values: np.ndarray  # shape (n_times, n_depths)
    last_access: float = field(default_factory=time.time)


Entry = PltEntry | DatEntry


class Store:
    def __init__(self) -> None:
        self._entries: dict[str, Entry] = {}

    def add_plt(self, parsed: ParsedPlt) -> PltMeta:
        self._purge_expired()
        file_id = uuid.uuid4().hex
        entry = PltEntry(variables=parsed.variables, dims=parsed.dims, grid=parsed.grid)
        self._entries[file_id] = entry
        return self._build_plt_meta(file_id, entry)

    def add_dat(self, variable: str, parsed: ParsedDat) -> DatMeta:
        self._purge_expired()
        file_id = uuid.uuid4().hex
        entry = DatEntry(
            variable=variable,
            grid=parsed.grid,
            depths=parsed.depths,
            depth_values=parsed.depth_values,
            times=parsed.times,
            values=parsed.values,
        )
        self._entries[file_id] = entry
        return self._build_dat_meta(file_id, entry)

    def get_entry(self, file_id: str) -> PltEntry:
        entry = self._entries.get(file_id)
        if not isinstance(entry, PltEntry):
            raise KeyError(file_id)
        entry.last_access = time.time()
        return entry

    def get_dat_entry(self, file_id: str) -> DatEntry:
        entry = self._entries.get(file_id)
        if not isinstance(entry, DatEntry):
            raise KeyError(file_id)
        entry.last_access = time.time()
        return entry

    def get_meta(self, file_id: str) -> PltMeta | DatMeta:
        entry = self._entries.get(file_id)
        if entry is None:
            raise KeyError(file_id)
        entry.last_access = time.time()
        if isinstance(entry, PltEntry):
            return self._build_plt_meta(file_id, entry)
        return self._build_dat_meta(file_id, entry)

    def delete(self, file_id: str) -> None:
        self._entries.pop(file_id, None)

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [fid for fid, e in self._entries.items() if now - e.last_access > SESSION_TTL_SECONDS]
        for fid in expired:
            self._entries.pop(fid, None)

    @staticmethod
    def _build_plt_meta(file_id: str, entry: PltEntry) -> PltMeta:
        idx_var = {name: i for i, name in enumerate(entry.variables)}
        grid = entry.grid

        x_coords = grid[0, 0, :, idx_var["X"]].astype(float).tolist()
        y_coords = grid[0, :, 0, idx_var["Y"]].astype(float).tolist()
        z_coords = grid[:, 0, 0, idx_var["Z"]].astype(float).tolist()

        value_ranges: dict[str, list[float]] = {}
        for name, i in idx_var.items():
            col = grid[..., i].astype(float)
            valid = col[~np.isclose(col, MISSING_VALUE)]
            if valid.size > 0:
                value_ranges[name] = [float(valid.min()), float(valid.max())]

        return PltMeta(
            file_id=file_id,
            variables=entry.variables,
            dims=Dims(**entry.dims),
            coords=Coords(X=x_coords, Y=y_coords, Z=z_coords),
            value_ranges=value_ranges,
        )

    @staticmethod
    def _build_dat_meta(file_id: str, entry: DatEntry) -> DatMeta:
        return DatMeta(
            file_id=file_id,
            variable=entry.variable,
            grid=DatGrid(**entry.grid),
            depths=entry.depths,
            depth_values=entry.depth_values,
            time_range=[float(entry.times.min()), float(entry.times.max())],
            n_times=int(entry.times.shape[0]),
        )


store = Store()
