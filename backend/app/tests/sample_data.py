"""テスト・E2E 用の合成データ生成。

実データ（研究室の計算結果）はリポジトリに含められないため、本物と同じ形式の
小さな .plt / .dat / input.dat と、それらを並べた計算結果ディレクトリを生成する。
値は格子インデックスの一次式にしてあり、テスト側で期待値を計算し直せる。

CLI として実行すると、指定ディレクトリに計算結果ディレクトリを書き出す（E2E 用）:

    python -m app.tests.sample_data <出力先>
"""

import sys
from pathlib import Path

from app.config import MISSING_VALUE

PLT_VARIABLES = ["X", "Y", "Z", "U", "V", "W", "TEMP", "SAL", "DOX"]
DX = 10.0
Z_LEVELS = [-4.0, -3.0, -2.0, -1.0]

INPUT_TEMPLATE_LINES = [
    "1 5 0 1 1 0             #isw",
    "{dims}",
    "0.0                     #bear",
    "0.8                     #dt",
    "7200.  1  0             #endtime,ntime,irst",
    "3600.                   #dispout",
    "3600.  0.   999999999999.   #fifit1,3,4",
    "{fifit2}",
    "{dx}                    #dx",
    "{z_levels}   #z(k)",
    "0.1 0.1 0.001 0.001 0   #am0,ac0,fkm0,fkc0,alat",
    "1.0e-6 1.0e-6           #fkmmin,fkcmin",
    "1.0e-4 1.0e-4           #fkm_in,fkc_in",
    "1                       #jsw1",
    "1                       #jsw2",
    "2                       #nopen",
    "0                       #nriv",
    "{milb_mjlb}",
    "0                       #i3d",
    "1.0 1.e-6 30            #cst,eps,nend",
    "{nhist_histout}",
    "{ijhist0}",
    "data/depth.dat",
    "data/grit0.dat",
    "data/qini.dat",
    "data/ginit_0.dat",
    "wind/wind.dat",
    "river/",
    "clim/himeji.dat",
    "obc/north.dat obc/south.dat",
    "hist",
    "field1",
    "field2",
]


def temp_value(i: int, j: int, k: int, t: int = 0) -> float:
    """合成 TEMP の解析解。テストで期待値を再計算するために公開している。"""
    return 20.0 + 0.1 * i + 0.2 * j + 0.5 * k + t


def is_land(i: int, j: int) -> bool:
    """i=0 の列を陸地（欠損）とする。"""
    return i == 0


def make_plt_text(ni: int = 4, nj: int = 5, nk: int = 3, t: int = 0) -> str:
    """Tecplot POINT 形式。K→J→I の順（I が最速）で1行1格子点。nk は Z_LEVELS の長さまで。"""
    lines = [
        f"Title=No.{t:05d} data",
        "VARIABLES=" + ",".join(PLT_VARIABLES),
        f"ZONE I= {ni}, J= {nj}, K= {nk}, F=POINT",
    ]
    for k in range(nk):
        for j in range(nj):
            for i in range(ni):
                x, y, z = i * DX, j * DX, Z_LEVELS[k]
                if is_land(i, j):
                    u = v = w = temp = sal = dox = MISSING_VALUE
                else:
                    u, v, w = 0.1 * i, 0.05 * j, 0.01 * k
                    temp = temp_value(i, j, k, t)
                    sal = 30.0 + 0.01 * j
                    dox = 2.0 + 0.5 * k + t
                lines.append(" ".join(f"{val:.6f}" for val in (x, y, z, u, v, w, temp, sal, dox)))
    return "\n".join(lines) + "\n"


def make_dat_text(i: int = 2, j: int = 3, n: int = 1, n_times: int = 4) -> str:
    """hist の時系列形式。深度ラベル列 × 時刻行。"""
    depths = [-1.75, -0.75, 0.25]
    lines = [
        f"i= {i} j= {j} n= {n} h= 4.0",
        "time[sec]  " + "  ".join(f"{d:.2f}m" for d in depths),
    ]
    for step in range(n_times):
        time_sec = 300.0 * (step + 1)
        values = [2000.0 + 10.0 * step + d for d in depths]
        lines.append(f"{time_sec:.1f}  " + "  ".join(f"{v:.7E}" for v in values))
    return "\n".join(lines) + "\n"


def make_input_dat_text(
    ni: int = 4,
    nj: int = 5,
    nk: int = 3,
    nest: int = 1,
    ifit2: float = 3600.0,
    points: list[tuple[int, int, int]] | None = None,
    milb_mjlb: str = "0 0 #miflib",
) -> str:
    points = points if points is not None else [(2, 3, 1), (3, 4, 1)]
    return (
        "\n".join(INPUT_TEMPLATE_LINES).format(
            dims=f"{ni} {nj} {nk} {nest} #in,jn,kn,nest",
            fifit2=f"{ifit2}  0.   999999999999. #fifit2,5,6",
            dx=DX,
            z_levels=" ".join(str(z) for z in Z_LEVELS[:nk]),
            milb_mjlb=milb_mjlb,
            nhist_histout=f"{len(points)}  300.0           #nhist,histout",
            ijhist0=" ".join(f"{i} {j} {n}" for i, j, n in points) + "   #ijhist0",
        )
        + "\n"
    )


def write_simulation_dir(root: Path, n_frames: int = 3, ni: int = 4, nj: int = 5, nk: int = 3) -> Path:
    """input.dat / field2 / hist を持つ計算結果ディレクトリを root に作る。"""
    root.mkdir(parents=True, exist_ok=True)
    (root / "input.dat").write_text(make_input_dat_text(ni, nj, nk))
    field2 = root / "field2"
    hist = root / "hist"
    field2.mkdir(exist_ok=True)
    hist.mkdir(exist_ok=True)
    (root / "field1").mkdir(exist_ok=True)
    for t in range(n_frames):
        (field2 / f"tec-{t:05d}.plt").write_text(make_plt_text(ni, nj, nk, t))
    for param in ("TEMP", "DOX"):
        for point in ("01", "02"):
            (hist / f"{param}-{point}.dat").write_text(make_dat_text())
    return root


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m app.tests.sample_data <output-dir>")
    print(write_simulation_dir(Path(sys.argv[1])))
