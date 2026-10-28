"""ディレクトリモードのセッション管理（アップロード方式の store.py と対の構造）。

input.dat のパース結果・field2/hist の走査結果を dir_id 単位で保持する。
"""

import time
import uuid
from dataclasses import dataclass, field

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
    last_access: float = field(default_factory=time.time)


class DirectoryStore:
    def __init__(self) -> None:
        self._entries: dict[str, DirectoryEntry] = {}

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
        self._purge_expired()
        dir_id = uuid.uuid4().hex
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
        self._entries[dir_id] = entry
        return self._build_meta(dir_id, entry)

    def get(self, dir_id: str) -> DirectoryEntry:
        entry = self._entries.get(dir_id)
        if entry is None:
            raise KeyError(dir_id)
        entry.last_access = time.time()
        return entry

    def get_meta(self, dir_id: str) -> DirectoryMeta:
        entry = self.get(dir_id)
        return self._build_meta(dir_id, entry)

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [did for did, e in self._entries.items() if now - e.last_access > SESSION_TTL_SECONDS]
        for did in expired:
            self._entries.pop(did, None)

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


directory_store = DirectoryStore()
