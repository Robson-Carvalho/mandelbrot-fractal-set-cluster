#!/usr/bin/env python3
"""Compara os dois algoritmos (balanceado x SPMD sem balanceamento) com graficos.

Uso: python compare_scaling.py --notes src/notes [--out src/notes/analise]
Le a execucao COMPLETA mais recente (DONE + P=1) de strong-*/weak-* em
<notes>/mandelbrot e <notes>/mandelbrot_spmd. Metrica: Tmax entre ranks (MPI_Wtime).
"""
import argparse
import glob
import os
import re
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--notes", required=True)
ap.add_argument("--out")
args = ap.parse_args()
NOTES = os.path.abspath(args.notes)
OUT = os.path.abspath(args.out or os.path.join(NOTES, "analise"))
os.makedirs(OUT, exist_ok=True)

ALGS = {  # pasta -> (rotulo, cor, marcador)
    "mandelbrot": ("Balanceado (mandelbrot)", "#2a6fdb", "o"),
    "mandelbrot_spmd": ("Sem balanceamento (SPMD)", "#d9534f", "s"),
}
RE_FILE = re.compile(r"-P(\d+)-r(\d+)\.out$")
RE_STAT = re.compile(r"^\s*(\w+)\s*:\s*Tmax=([\d.]+) s \| Tmin=([\d.]+) s \| Media=([\d.]+) s \| Desvio=([\d.]+) s")


def latest(base, prefix):
    dirs = sorted(
        d for d in glob.glob(os.path.join(base, f"{prefix}-2*"))
        if os.path.isfile(os.path.join(d, "DONE")) and glob.glob(os.path.join(d, f"{prefix}-P1-r*.out"))
    )
    if not dirs:
        sys.exit(f"Nenhuma pasta '{prefix}-*' completa em {base}")
    return dirs[-1]


def load(directory, prefix):
    data = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(directory, f"{prefix}-P*-r*.out"))):
        m = RE_FILE.search(f)
        if not m:
            continue
        stats = {}
        with open(f, errors="replace") as fh:
            for line in fh:
                s = RE_STAT.match(line)
                if s:
                    stats[s.group(1)] = tuple(float(s.group(i)) for i in range(2, 6))
        if "Ttotal" in stats:
            data[int(m.group(1))].append(stats)
    return dict(sorted(data.items()))


def series(d, metric, idx=0):
    """Media entre execucoes do valor idx (0=Tmax,1=Tmin,2=Media) da metrica."""
    Ps = np.array(list(d))
    return Ps, np.array([np.mean([r[metric][idx] for r in d[p]]) for p in Ps])


DATA = {}
for alg in ALGS:
    base = os.path.join(NOTES, alg)
    sdir, wdir = latest(base, "strong"), latest(base, "weak")
    print(f"{alg}:\n  {sdir}\n  {wdir}")
    DATA[alg] = (load(sdir, "strong"), load(wdir, "weak"))

plt.rcParams.update({"figure.dpi": 130, "axes.grid": True, "grid.alpha": .3, "font.size": 10})


def new(title, xlabel="Processos (P)", ylabel=""):
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    return fig, ax


def finish(fig, ax, name, Ps):
    ax.set_xticks(Ps)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name))
    plt.close(fig)


def line(ax, alg, Ps, y, **kw):
    lab, c, mk = ALGS[alg]
    ax.plot(Ps, y, marker=mk, color=c, label=lab, **kw)
    for p, v in zip(Ps, y):
        ax.annotate(f"{v:.2f}" if v < 20 else f"{v:.0f}", (p, v), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=7, color=c)


# ---- Strong ----
fig, ax = new("Strong scaling: tempo de execução", ylabel="Tmax médio (s)")
for a in ALGS:
    Ps, t = series(DATA[a][0], "Ttotal")
    line(ax, a, Ps, t)
ax.set_yscale("log")
finish(fig, ax, "comparacao_strong_tempo.png", Ps)

fig, ax = new("Strong scaling: speedup", ylabel="Speedup")
for a in ALGS:
    Ps, t = series(DATA[a][0], "Ttotal")
    line(ax, a, Ps, t[0] / t)
ax.plot(Ps, Ps, "--", color="gray", label="Ideal (S = P)")
finish(fig, ax, "comparacao_strong_speedup.png", Ps)

fig, ax = new("Strong scaling: eficiência", ylabel="Eficiência")
for a in ALGS:
    Ps, t = series(DATA[a][0], "Ttotal")
    line(ax, a, Ps, t[0] / t / Ps)
ax.axhline(1, ls="--", color="gray", label="Ideal")
ax.set_ylim(0, 1.15)
finish(fig, ax, "comparacao_strong_eficiencia.png", Ps)

fig, ax = new("Strong scaling: tempo de comunicação (Tcomm)", ylabel="Tcomm Tmax médio (s)")
for a in ALGS:
    Ps, t = series(DATA[a][0], "Tcomm")
    line(ax, a, Ps, t)
finish(fig, ax, "comparacao_strong_comunicacao.png", Ps)

fig, ax = new("Strong scaling: desbalanceamento de carga", ylabel="Tcomp: Tmax / Tmédia")
for a in ALGS:
    Ps, tmx = series(DATA[a][0], "Tcomp", 0)
    _, tmd = series(DATA[a][0], "Tcomp", 2)
    line(ax, a, Ps, tmx / tmd)
ax.axhline(1, ls="--", color="gray", label="Balanceamento perfeito")
finish(fig, ax, "comparacao_strong_desbalanceamento.png", Ps)

# ---- Weak ----
fig, ax = new("Weak scaling: tempo de execução", ylabel="Tmax médio (s)")
for a in ALGS:
    Ps, t = series(DATA[a][1], "Ttotal")
    line(ax, a, Ps, t)
    ref = t[0]
ax.axhline(ref, ls="--", color="gray", label="Ideal (constante)")
ax.set_ylim(0, None)
finish(fig, ax, "comparacao_weak_tempo.png", Ps)

fig, ax = new("Weak scaling: eficiência (T1/TP)", ylabel="Eficiência fraca")
for a in ALGS:
    Ps, t = series(DATA[a][1], "Ttotal")
    line(ax, a, Ps, t[0] / t)
ax.axhline(1, ls="--", color="gray", label="Ideal")
ax.set_ylim(0, 1.15)
finish(fig, ax, "comparacao_weak_eficiencia.png", Ps)

print(f"\nImagens salvas em {OUT}")
