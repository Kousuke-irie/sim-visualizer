"""テスト・E2E 用の合成データ生成。

実データ（研究室の計算結果）はリポジトリに含められないため、本物と同じ形式の
小さな .plt / .dat / input.dat と、それらを並べた計算結果ディレクトリを生成する。
値は格子インデックスの一次式にしてあり、テスト側で期待値を計算し直せる。

CLI として実行すると、指定ディレクトリに計算結果ディレクトリを書き出す（E2E 用）:

    python -m app.tests.sample_data <出力先> [--temp-offset 1.5] [--ni 3] [--model-files]
"""

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


def make_plt_text(ni: int = 4, nj: int = 5, nk: int = 3, t: int = 0, temp_offset: float = 0.0) -> str:
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
                    temp = temp_value(i, j, k, t) + temp_offset  # 比較テスト用に TEMP だけずらせる
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
    with_fkm_in: bool = True,
) -> str:
    """with_fkm_in=False で、fkm_in,fkc_in 行を持たない古い版（v2 など）の行構成にする。"""
    points = points if points is not None else [(2, 3, 1), (3, 4, 1)]
    lines = [line for line in INPUT_TEMPLATE_LINES if with_fkm_in or "#fkm_in" not in line]
    return (
        "\n".join(lines).format(
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


# eco.h（生態系パラメータの data 文）を縮めたもの。新しいランの作成で値を書き換えるテストに使う
ECO_H_TEXT = """\
\t\tdouble precision,dimension(Np) :: PHY
\t\tdata Alp1/1.04167d-05/
\t\tdata Iopt/54.7/
\t\tdata aKp/0.0106/
"""


def make_mecnest_source(with_fkm_in: bool) -> str:
    """mecnest.f90 の input.dat 読み込み部分だけを模した最小のソース（版の判定に使う部分）。"""
    lines = [
        "      open(10,file='input.dat')",
        "      read(10,*) (isw(i),i=1,6)",
        "      read(10,*) am0,ac0,fkm0,fkc0,alat",
        "      read(10,*) fkmmin,fkcmin",
    ]
    if with_fkm_in:
        lines.append("      read(10,*) fkm_in,fkc_in                ! isw(2)=5用: モバ内部の拡散係数")
    lines.append("      read(10,*) (jsw(1,n),n=1,nast)")
    return "\n".join(lines) + "\n"


def write_simulation_dir(
    root: Path,
    n_frames: int = 3,
    ni: int = 4,
    nj: int = 5,
    nk: int = 3,
    with_fkm_in: bool = True,
    with_source: bool = False,
    ifit2: float = 3600.0,
    temp_offset: float = 0.0,
    points: list[tuple[int, int, int]] | None = None,
    with_eco: bool = False,
) -> Path:
    """input.dat / field2 / hist を持つ計算結果ディレクトリを root に作る。

    with_fkm_in で input.dat の版（fkm_in,fkc_in 行の有無）を、with_source で mecnest.f90 を置くかを選ぶ。
    ifit2 は出力間隔[秒]（フレーム t の時刻は t*ifit2）、temp_offset は TEMP に足す値（2ケース比較のテスト用）。
    points は hist 地点の (i, j, n)。既定は (2, 3, 1) と (3, 4, 1)。
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "input.dat").write_text(
        make_input_dat_text(ni, nj, nk, ifit2=ifit2, points=points, with_fkm_in=with_fkm_in)
    )
    if with_source:
        (root / "mecnest.f90").write_text(make_mecnest_source(with_fkm_in))
    if with_eco:
        (root / "eco.h").write_text(ECO_H_TEXT)
    field2 = root / "field2"
    hist = root / "hist"
    field2.mkdir(exist_ok=True)
    hist.mkdir(exist_ok=True)
    (root / "field1").mkdir(exist_ok=True)
    for t in range(n_frames):
        (field2 / f"tec-{t:05d}.plt").write_text(make_plt_text(ni, nj, nk, t, temp_offset))
    for param in ("TEMP", "DOX"):
        for point in ("01", "02"):
            (hist / f"{param}-{point}.dat").write_text(make_dat_text())
    return root


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="E2E 用の合成計算結果ディレクトリを書き出す")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--temp-offset", type=float, default=0.0, help="TEMP に足す値（2ケース比較用）")
    parser.add_argument("--ni", type=int, default=4, help="I 方向の格子数（格子が違うランを作る用）")
    parser.add_argument("--model-files", action="store_true", help="mecnest.f90 と eco.h も置く（新しいランの作成用）")
    args = parser.parse_args()
    print(
        write_simulation_dir(
            args.output_dir,
            ni=args.ni,
            temp_offset=args.temp_offset,
            with_source=args.model_files,
            with_eco=args.model_files,
        )
    )
