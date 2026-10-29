"""テスト用の偽のモデル（偽の gfortran が作る a.out から起動される。sample_data.write_fake_toolchain を参照）。

本物の mecamamo と同じく、カレントディレクトリの input.dat を読み、endtime / ifit2 + 1 枚の tec-*.plt を
field2 に1枚ずつ書き出す。1枚ごとに FAKE_MODEL_FRAME_SECONDS 秒（既定 0.2）待つので、進捗・中止を試せる。
FAKE_MODEL_EXIT を設定すると、書き終えたあとその終了コードで終わる（計算の異常終了を模す）。
格子は合成データの既定（4x5x3）で書く。
"""

import os
import sys
import time
from pathlib import Path

from app.parsers.input_parser import parse_input_dat, source_reads_fkm_in
from app.tests.sample_data import make_dat_text, make_plt_text


def main() -> int:
    run = Path.cwd()
    source = run / "mecnest.f90"
    with_fkm_in = source_reads_fkm_in(source.read_text()) if source.is_file() else True
    parsed = parse_input_dat((run / "input.dat").read_text(), with_fkm_in=with_fkm_in)
    field2 = run / parsed.result_dirs["field2"]
    hist = run / parsed.result_dirs["hist"]
    delay = float(os.environ.get("FAKE_MODEL_FRAME_SECONDS", "0.2"))

    n_frames = round(parsed.endtime / parsed.ifit2) + 1
    for t in range(n_frames):
        if t > 0:
            time.sleep(delay)
        (field2 / f"tec-{t:05d}.plt").write_text(make_plt_text(t=t))
        print(f"time = {t * parsed.ifit2:.1f} s", flush=True)
    for param in ("TEMP", "DOX"):
        for n in range(1, parsed.nhist + 1):
            (hist / f"{param}-{n:02d}.dat").write_text(make_dat_text())
    print("fake model: done", flush=True)
    return int(os.environ.get("FAKE_MODEL_EXIT", "0"))


if __name__ == "__main__":
    sys.exit(main())
