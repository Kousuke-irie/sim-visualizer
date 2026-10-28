"""ディレクトリモードのセッション管理（アップロード方式の store.py と対の構造）。

input.dat のパース結果・field2/hist の走査結果を dir_id 単位で保持する。
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

from app.config import SESSION_TTL_SECONDS
from app.models.common import Dims
from app.models.directory import (
    DirectoryInputMeta,
    DirectoryMeta,
    HistPoint,
    PltFrameMeta,
    ResultDirs,
    TimeseriesIndex,
)
from app.parsers.dir_scanner import PltFrameRaw, TimeseriesIndexRaw
from app.parsers.input_parser import ParsedInput
from app.parsers.plt_parser import ParsedPlt
from app.services.plt_cache import plt_cache
from app.services.ttl_store import TTLStore


@dataclass
class DirectoryEntry:
    root: str
    field2_dir: str
    hist_dir: str
    parsed_input: ParsedInput
    plt_frames: list[PltFrameRaw]
    ts_index: TimeseriesIndexRaw
    plt_variables: list[str]
    plt_dims: dict[str, int]


class DirectoryStore:
    def __init__(
        self,
        clock: Callable[[], float] = time.time,
        on_expire: Callable[[str, DirectoryEntry], None] | None = None,
    ) -> None:
        self._entries: TTLStore[DirectoryEntry] = TTLStore(SESSION_TTL_SECONDS, clock=clock, on_expire=on_expire)

    def add(
        self,
        root: str,
        field2_dir: str,
        hist_dir: str,
        parsed_input: ParsedInput,
        plt_frames: list[PltFrameRaw],
        ts_index: TimeseriesIndexRaw,
        first_frame: ParsedPlt,
    ) -> DirectoryMeta:
        entry = DirectoryEntry(
            root=root,
            field2_dir=field2_dir,
            hist_dir=hist_dir,
            parsed_input=parsed_input,
            plt_frames=plt_frames,
            ts_index=ts_index,
            plt_variables=first_frame.variables,
            plt_dims=first_frame.dims,
        )
        return self._build_meta(self._entries.add(entry), entry)

    def get(self, dir_id: str) -> DirectoryEntry:
        return self._entries.get(dir_id)

    def get_meta(self, dir_id: str) -> DirectoryMeta:
        return self._build_meta(dir_id, self.get(dir_id))

    @staticmethod
    def _build_meta(dir_id: str, entry: DirectoryEntry) -> DirectoryMeta:
        parsed = entry.parsed_input
        return DirectoryMeta(
            dir_id=dir_id,
            root=entry.root,
            input=DirectoryInputMeta(
                ifit2=parsed.ifit2,
                endtime=parsed.endtime,
                dt=parsed.dt,
                dx=parsed.dx,
                z_levels=parsed.z_levels,
                nhist=parsed.nhist,
                histout=parsed.histout,
                result_dirs=ResultDirs(**parsed.result_dirs),
            ),
            points=[HistPoint(point=p.point, i=p.i, j=p.j, n=p.n) for p in parsed.points],
            plt_frames=[PltFrameMeta(file=f.file, index=f.index, time_sec=f.time_sec) for f in entry.plt_frames],
            timeseries=TimeseriesIndex(params=entry.ts_index.params, by_param=entry.ts_index.by_param),
            plt_variables=entry.plt_variables,
            plt_dims=Dims(**entry.plt_dims),
        )


# 期限切れのディレクトリのフレームは二度と参照されないので、LRU で押し出されるのを待たずに捨てる
directory_store = DirectoryStore(on_expire=lambda dir_id, _entry: plt_cache.invalidate_dir(dir_id))
