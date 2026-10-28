#!/usr/bin/env python3
"""
Tecplot POINT形式ファイル (tec-00022.plt) から、指定したX位置での
YZ断面（縦断面）での濃度分布を可視化するスクリプト。

VARIABLES = X, Y, Z, U, V, W, TEMP, SAL, DIC, TAlk, PHY, ZOO, POC, DOC, DIP, DIN, DOX
ZONE      = I=31, J=61, K=21, F=POINT
欠損値    = -999.0 (陸地・境界)
"""

import re
import numpy as np
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# 設定
# ------------------------------------------------------------------
FILENAME = "tec-00003.plt"
VARIABLE = "TEMP"             # 描画する変数名
X_TARGET = 150.0            # 描画するYZ断面のX位置 [m]（最も近い列を自動選択）
MISSING  = -999.0

# 流速ベクトル（矢印）の設定 … YZ断面なので V(南北) と W(鉛直) を使う
SHOW_VECTORS = True
VEC_SKIP     = 2
VEC_SCALE    = None

VARS = ["X", "Y", "Z", "U", "V", "W", "TEMP", "SAL", "DIC", "TAlk",
        "PHY", "ZOO", "POC", "DOC", "DIP", "DIN", "DOX"]

# ------------------------------------------------------------------
# データ読み込み
# ------------------------------------------------------------------
def read_tecplot(filename):
    I = J = K = None
    data_lines = []
    with open(filename, "r") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            up = s.upper()
            if up.startswith("TITLE") or up.startswith("VARIABLES"):
                continue
            if up.startswith("ZONE"):
                I = int(re.search(r"I\s*=\s*(\d+)", up).group(1))
                J = int(re.search(r"J\s*=\s*(\d+)", up).group(1))
                K = int(re.search(r"K\s*=\s*(\d+)", up).group(1))
                continue
            data_lines.append(s)
    data = np.array([[float(v) for v in ln.split()] for ln in data_lines])
    return data, I, J, K


data, I, J, K = read_tecplot(FILENAME)
print(f"格子寸法: I={I}, J={J}, K={K}  読み込み点数={len(data)}")

idx = {name: n for n, name in enumerate(VARS)}
grid = data.reshape(K, J, I, len(VARS))   # (K, J, I, var)

Y = grid[:, :, :, idx["Y"]]
Z = grid[:, :, :, idx["Z"]]
X = grid[:, :, :, idx["X"]]
C = grid[:, :, :, idx[VARIABLE]]
V = grid[:, :, :, idx["V"]]   # 南北流速
W = grid[:, :, :, idx["W"]]   # 鉛直流速

# ------------------------------------------------------------------
# 目的のX列を選択（YZ断面）
# ------------------------------------------------------------------
x_coords = X[0, 0, :]                       # I方向のX値
i_sel = int(np.argmin(np.abs(x_coords - X_TARGET)))
x_actual = x_coords[i_sel]
print(f"選択したX断面: i={i_sel}, X={x_actual:.1f} m (目標 {X_TARGET} m)")

# YZ平面 (K, J) を取り出す
y2d = Y[:, :, i_sel]        # (K, J)
z2d = Z[:, :, i_sel]
c2d = C[:, :, i_sel].astype(float)
v2d = V[:, :, i_sel].astype(float)
w2d = W[:, :, i_sel].astype(float)

# 欠損マスク
c2d = np.ma.masked_where(np.isclose(c2d, MISSING), c2d)
vmask = np.isclose(v2d, MISSING) | np.isclose(w2d, MISSING)
v2d = np.ma.masked_where(vmask, v2d)
w2d = np.ma.masked_where(vmask, w2d)

# ------------------------------------------------------------------
# 描画（横軸 Y、縦軸 Z）
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5))

cf = ax.contourf(y2d, z2d, c2d, levels=30, cmap="viridis")
cbar = fig.colorbar(cf, ax=ax)
cbar.set_label(f"{VARIABLE}")

cs = ax.contour(y2d, z2d, c2d, levels=10, colors="gray",
                linewidths=0.4, alpha=0.5)

if SHOW_VECTORS:
    s = VEC_SKIP
    q = ax.quiver(y2d[::s, ::s], z2d[::s, ::s],
                  v2d[::s, ::s], w2d[::s, ::s],
                  color="black", scale=VEC_SCALE,
                  width=0.003, pivot="mid")
    spd = np.sqrt(v2d**2 + w2d**2)
    ref = float(np.nanmax(spd)) if np.isfinite(np.nanmax(spd)) else 1.0
    ref = round(ref, 2) if ref > 0 else 1.0
    ax.quiverkey(q, 0.80, 1.05, ref, f"{ref} m/s",
                 labelpos="E", coordinates="axes")

ax.set_xlabel("Y [m]")
ax.set_ylabel("Z [m] (depth)")
ax.set_title(f"{VARIABLE} distribution on YZ-section at X = {x_actual:.1f} m", pad=20)

# 水柱（有効データ範囲）に縦軸を限定
zvalid = z2d[~c2d.mask] if np.ma.is_masked(c2d) else z2d
ax.set_ylim(np.min(zvalid), max(0.0, np.max(zvalid)))

plt.tight_layout()
out = f"yzsection_{VARIABLE}_x{x_actual:.0f}.png"
plt.savefig(out, dpi=150)
print(f"保存: {out}")
plt.show()