#!/usr/bin/env python3
"""Grafico do baseline serial: tempo por execucao e comparacao com MPI P=1.

Uso: python utils/plot_serial.py --notes src/notes
Salva src/notes/serial/serial_tempo.png e serial_vs_mpi_p1.png
"""
import argparse
import glob
import os
import re

import matplotlib.pyplot as plt
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--notes", default="src/notes")
args = ap.parse_args()
NOTES = os.path.abspath(args.notes)


def latest(base, prefix, need="*.out"):
    dirs = sorted(d for d in glob.glob(os.path.join(base, f"{prefix}-2*"))
                  if os.path.isfile(os.path.join(d, "DONE")) and glob.glob(os.path.join(d, need)))
    return dirs[-1] if dirs else None


def grab(path, key):
    m = re.search(rf"^\s*{key}\s*=\s*([\d.]+)", open(path).read(), re.M)
    return float(m.group(1)) if m else None


def tmax_p1(base):
    """Media do Tmax de Ttotal nas execucoes strong P=1 (linha de estatistica reduzida)."""
    d = latest(base, "strong", "strong-P1-r*.out")
    if not d:
        return None
    vals = []
    for f in glob.glob(os.path.join(d, "strong-P1-r*.out")):
        m = re.search(r"^\s*Ttotal\s*:\s*Tmax=([\d.]+)", open(f).read(), re.M)
        if m:
            vals.append(float(m.group(1)))
    return np.mean(vals) if vals else None


sdir = latest(os.path.join(NOTES, "serial"), "serial")
outs = sorted(glob.glob(os.path.join(sdir, "serial-r*.out")))
comp = np.array([grab(f, "Tcomp") for f in outs])
tio = np.array([grab(f, "Tio") for f in outs])
print(f"Usando: {sdir}")
print(f"Tcomp: media={comp.mean():.3f} s  desvio={comp.std(ddof=1):.4f} s")
print(f"Tio  : media={tio.mean():.3f} s  desvio={tio.std(ddof=1):.4f} s")


OUTDIR = os.path.join(NOTES, "serial")

# ---------- Grafico 1: tempo do serial em cada execucao ----------
# Cada barra = 1 execucao do programa serial. Azul = tempo de calculo (Ttotal);
# laranja = gravacao da imagem (Tio), medida mas fora do Ttotal.
fig, ax = plt.subplots(figsize=(7, 5))
labels = [f"Execução {i + 1}" for i in range(len(outs))]
ax.bar(labels, comp, color="#2a6fdb", label="Cálculo do fractal (Tcomp = Ttotal)")
ax.bar(labels, tio, bottom=comp, color="#f0ad4e", label="Gravação da imagem (Tio, fora do Ttotal)")
for i, (c, t) in enumerate(zip(comp, tio)):
    ax.text(i, c / 2, f"{c:.2f} s", ha="center", color="white", fontweight="bold", fontsize=12)
    ax.text(i, c + t + 3, f"+ {t:.1f} s", ha="center", fontsize=9, color="#a0661a")
ax.set(ylabel="Tempo (s)", ylim=(0, (comp + tio).max() * 1.15),
       title=f"Tempo do programa serial\nmédia = {comp.mean():.2f} s  (desvio = {comp.std(ddof=1):.3f} s)")
ax.legend(loc="lower center")
fig.tight_layout()
out1 = os.path.join(OUTDIR, "serial_tempo.png")
fig.savefig(out1, dpi=150)
plt.close(fig)

# ---------- Grafico 2: serial x MPI rodando com 1 processo ----------
# Mesma imagem, 1 processo so. Se os tempos sao iguais, o MPI nao adiciona custo,
# entao usar T(P=1) do MPI como base do speedup equivale a usar o serial.
names, vals, colors = ["Serial"], [comp.mean()], ["#2a6fdb"]
for name, sub, col in [("MPI otimizado\n(1 processo)", "mandelbrot", "#2a9d5c"),
                       ("MPI ingênuo (SPMD)\n(1 processo)", "mandelbrot_spmd", "#d9534f")]:
    v = tmax_p1(os.path.join(NOTES, sub))
    if v is not None:
        names.append(name), vals.append(v), colors.append(col)
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(names, vals, color=colors)
for i, v in enumerate(vals):
    txt = f"{v:.2f} s" if i == 0 else f"{v:.2f} s\n({(v / vals[0] - 1) * 100:+.2f}%)"
    ax.text(i, v / 2, txt, ha="center", color="white", fontweight="bold", fontsize=12)
ax.set(ylabel="Tempo de cálculo (s)", ylim=(0, max(vals) * 1.1),
       title="Serial x MPI com 1 processo\n(diferença ≈ 0 → MPI não adiciona custo)")
fig.tight_layout()
out2 = os.path.join(OUTDIR, "serial_vs_mpi_p1.png")
fig.savefig(out2, dpi=150)
plt.close(fig)

old = os.path.join(OUTDIR, "serial_baseline.png")
if os.path.exists(old):
    os.remove(old)
print(f"Gerados: {out1}\n         {out2}")
