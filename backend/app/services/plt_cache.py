"""パース済み .plt (field2) の LRU キャッシュ。

時間スライダー操作のたびに約10MBの .plt を再パースするのは重いため、
`(dir_id, frame_index)` をキーに直近アクセスしたフレームを保持する。
"""

from collections import OrderedDict

from app.parsers.plt_parser import ParsedPlt, parse_plt_bytes

DEFAULT_CAPACITY = 8


class PltCache:
    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._capacity = capacity
        self._data: OrderedDict[tuple[str, int], ParsedPlt] = OrderedDict()

    def get_or_parse(self, dir_id: str, frame_index: int, path: str) -> ParsedPlt:
        key = (dir_id, frame_index)
        cached = self._data.get(key)
        if cached is not None:
            self._data.move_to_end(key)
            return cached

        with open(path, "rb") as f:
            content = f.read()
        parsed = parse_plt_bytes(content)
        self.put(dir_id, frame_index, parsed)
        return parsed

    def put(self, dir_id: str, frame_index: int, parsed: ParsedPlt) -> None:
        """別の経路でパース済みのフレームを登録する（ディレクトリを開いたときの最初のフレームなど）。"""
        key = (dir_id, frame_index)
        self._data[key] = parsed
        self._data.move_to_end(key)
        if len(self._data) > self._capacity:
            self._data.popitem(last=False)

    def invalidate_dir(self, dir_id: str) -> None:
        for key in [k for k in self._data if k[0] == dir_id]:
            self._data.pop(key, None)


plt_cache = PltCache()
