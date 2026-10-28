"""実データと同じ規模の .plt で、パース時間とピークメモリを計測する。

    python scripts/bench_plt_parser.py [繰り返し回数]

格子 31×61×21（約4万点）× 17変数、指数表記で約9.5MB（研究で扱う field2 の1フレームに相当）。
時間は繰り返しの最小値（他プロセスの影響を受けにくい）、メモリは tracemalloc によるピーク。
"""

import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import MISSING_VALUE  # noqa: E402  sys.path を通してから import する
from app.parsers.plt_parser import parse_plt_bytes  # noqa: E402

NI, NJ, NK = 31, 61, 21
VARIABLES = "X Y Z U V W TEMP SAL DIC TAlk PHY ZOO POC DOC DIP DIN DOX".split()


def make_content() -> bytes:
    rng = np.random.default_rng(0)
    lines = ["TITLE=bench", "VARIABLES=" + ",".join(VARIABLES), f"ZONE I={NI}, J={NJ}, K={NK}, F=POINT"]
    for k in range(NK):
        for j in range(NJ):
            for i in range(NI):
                row = rng.random(len(VARIABLES)) * 100
                row[:3] = (i * 10.0, j * 10.0, -float(k))
                if i == 0:
                    row[3:] = MISSING_VALUE
                lines.append(" ".join(f"{v:.7E}" for v in row))
    return ("\n".join(lines) + "\n").encode()


def main() -> None:
    repeat = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    content = make_content()

    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        parse_plt_bytes(content)
        times.append(time.perf_counter() - start)

    tracemalloc.start()
    parse_plt_bytes(content)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"file      : {len(content) / 1e6:.1f} MB, {NI * NJ * NK} points x {len(VARIABLES)} vars")
    print(f"parse     : min {min(times) * 1000:.1f} ms / median {sorted(times)[len(times) // 2] * 1000:.1f} ms")
    print(f"peak mem  : {peak / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
