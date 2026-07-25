"""Check web L/R thickness logic for twin box S1."""
import ezdxf
from src.dxf_reader import read_inpolys, _get_polyline_vertices
from src.frame_builder import build_twin_frame
from src.load_reader import read_loads

doc = ezdxf.readfile("data/TP_BL/S1.dxf")
msp = doc.modelspace()
out = _get_polyline_vertices(msp, "OUTPOLY")
inpolys = read_inpolys(msp)
ld = read_loads("data/Midas-Transverse-Boxgirder-analysis.xls")
frame = build_twin_frame(out, inpolys[0], inpolys[1], d_L=ld["d_L"], d_R=ld["d_R"])

wL = frame["web_left"]
wR = frame["web_right"]
of = frame["outer_features"]
inn_l = frame["inpoly_mct"]
inn_r = frame["inpoly_right_mct"]

print("=== OUTPOLY web junctions (MCT) ===")
print("web_junc_L", of["web_junc_L"], "bot_L", of["bot_L"])
print("web_junc_R", of["web_junc_R"], "bot_R", of["bot_R"])
print("gap", frame["gap_x_L"], frame["gap_x_R"])

print("\n=== Web LEFT nodes (sample) ===")
for i, n in enumerate(wL["nodes"][:4]):
    print(f"  [{i}] x={n['x']:.4f} z={n['z']:.4f} t={n['thickness']:.4f}")
print("  ... last 2:")
for n in wL["nodes"][-2:]:
    print(f"  x={n['x']:.4f} z={n['z']:.4f} t={n['thickness']:.4f}")

print("\n=== Web RIGHT nodes (sample) ===")
for i, n in enumerate(wR["nodes"][:4]):
    print(f"  [{i}] x={n['x']:.4f} z={n['z']:.4f} t={n['thickness']:.4f}")

print("\n=== Inner edge vertices (used for interpolation) ===")
print("L inner X:", [round(p[0], 3) for p in wL["inner_edge"]])
print("R inner X:", [round(p[0], 3) for p in wR["inner_edge"]])

x_gap_L = max(p[0] for p in inn_l)
x_gap_R = min(p[0] for p in inn_r)
xjL = of["web_junc_L"][0]
xjR = of["web_junc_R"][0]
t_top_L = wL["nodes"][0]["thickness"]
t_top_R = wR["nodes"][0]["thickness"]

print("\n=== Thickness check at web top ===")
exp_L = abs(xjL - x_gap_L)
exp_R = abs(xjR - x_gap_R)
print(f"L: expected ~{exp_L:.3f} m, actual t={t_top_L:.3f} m, match={abs(exp_L-t_top_L)<0.05}")
print(f"R: expected ~{exp_R:.3f} m, actual t={t_top_R:.3f} m, match={abs(exp_R-t_top_R)<0.05}")

x_west_L = min(p[0] for p in inn_l)
x_east_R = max(p[0] for p in inn_r)
print(f"\nIf wrongly used far void face:")
print(f"  L west x={x_west_L:.2f} -> bogus t={abs(xjL-x_west_L):.2f} m")
print(f"  R east x={x_east_R:.2f} -> bogus t={abs(xjR-x_east_R):.2f} m")
