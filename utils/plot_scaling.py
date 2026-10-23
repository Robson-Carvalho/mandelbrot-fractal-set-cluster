#!/usr/bin/env python3
"""Gera graficos de Strong/Weak Scaling a partir dos .out do Mandelbrot MPI.

Uso: python plot_scaling.py [--base PASTA] [--strong DIR] [--weak DIR]
  --base: pasta que contem strong-*/weak-* (obrigatorio na pratica; use `make plot-*`).
          Ex.: --base src/notes/mandelbrot_spmd. Os PNGs sao salvos nessa pasta.
  Sem --strong/--weak, usa a execucao COMPLETA mais recente (com DONE e P=1).
Metrica: Ttotal (Tmax entre ranks, medido com MPI_Wtime) de cada execucao.
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
ap.add_argument("--base", required=True)
ap.add_argument("--strong")
ap.add_argument("--weak")
args = ap.parse_args()
HERE = os.path.abspath(args.base)  # onde ficam as execucoes e onde os PNGs sao salvos


def latest(prefix):
    """Pasta <prefixo>-AAAAMMDD-HHMMSS completa mais recente (ordem do nome = cronologica)."""
    dirs = sorted(
        d for d in glob.glob(os.path.join(HERE, f"{prefix}-2*"))
        if os.path.isfile(os.path.join(d, "DONE")) and glob.glob(os.path.join(d, f"{prefix}-P1-r*.out"))
    )
    if not dirs:
        sys.exit(f"Nenhuma pasta '{prefix}-*' completa encontrada em {HERE}")
    return dirs[-1]


STRONG = args.strong or latest("strong")
WEAK = args.weak or latest("weak")
print(f"Usando: {STRONG}\n        {WEAK}\n")

RE_FILE = re.compile(r"-P(\d+)-r(\d+)\.out$")
RE_STAT = re.compile(r"^\s*(\w+)\s*:\s*Tmax=([\d.]+) s \| Tmin=([\d.]+) s \| Media=([\d.]+) s \| Desvio=([\d.]+) s")


def load(directory, prefix):
    """Retorna {P: [ {metrica: (max,min,media,desvio)} por execucao ]}."""
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


def tmax(runs, metric="Ttotal"):
    return np.array([r[metric][0] for r in runs])


def fit_amdahl(P, S):
    """Ajusta fracao serial f minimizando erro de S(P)=1/(f+(1-f)/P)."""
    fs = np.linspace(0, 1, 100001)
    err = [np.sum((1 / (f + (1 - f) / P) - S) ** 2) for f in fs[::50]]
    return fs[::50][int(np.argmin(err))]


def time_bars(ax, d, Ps, means, stds, title, ideal=None, xlabel="Processos (P)"):
    """Barras da media + pontos de cada execucao + desvio anotado."""
    x = np.arange(len(Ps))
    ax.bar(x, means, width=0.55, color="#2a6fdb", alpha=.55, label="Média")
    for i, p in enumerate(Ps):
        runs = tmax(d[p])
        ax.scatter(np.full(len(runs), i) + np.linspace(-.08, .08, len(runs)) if len(runs) > 1 else [i], runs,
                   s=22, color="#f0a030", edgecolor="k", linewidth=.4, zorder=3,
                   label="Execuções individuais" if i == 0 else None)
        ax.annotate(f"{means[i]:.1f} s\n(σ={stds[i]:.2f})", (i, max(runs.max(), means[i])),
                    textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)
    if ideal is not None:
        ax.axhline(ideal, ls="--", color="gray", label="Ideal (constante)")
    top = max(max(tmax(d[p]).max() for p in Ps), means.max())
    ax.set(xticks=x, xticklabels=[str(p) for p in Ps], xlabel=xlabel, ylabel="Tmax (s)",
           title=title, ylim=(0, top * 1.18))
    ax.legend()


def save_each(fig, axes, names):
    """Salva cada subplot (axes) como um PNG individual."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for a, n in zip(axes, names):
        bbox = a.get_tightbbox(r).expanded(1.05, 1.08).transformed(fig.dpi_scale_trans.inverted())
        fig.savefig(os.path.join(HERE, n), bbox_inches=bbox)


plt.rcParams.update({"figure.dpi": 130, "axes.grid": True, "grid.alpha": .3, "font.size": 10})

# ---------------- Strong ----------------
sd = load(STRONG, "strong")
Ps = np.array(list(sd))
mean = np.array([tmax(sd[p]).mean() for p in Ps])
std = np.array([tmax(sd[p]).std(ddof=1) if len(sd[p]) > 1 else 0 for p in Ps])
tser = mean[0]  # Tserial = T(P=1)
speed = tser / mean
eff = speed / Ps
f = fit_amdahl(Ps, speed)
Ppl = np.linspace(1, Ps.max(), 200)

print("STRONG: P | Tmax medio | desvio | speedup | eficiencia")
for p, m, s, sp, e in zip(Ps, mean, std, speed, eff):
    print(f"{p:3d} | {m:9.3f} | {s:7.3f} | {sp:6.3f} | {e:6.3f}")

fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
time_bars(ax[0], sd, Ps, mean, std, "Tempo de execução (média, execuções e desvio)")
ax[1].plot(Ps, speed, "o-", color="#2a6fdb", label="Medido")
ax[1].plot(Ppl, Ppl, "--", color="gray", label="Ideal (S = P)")
ax[1].set(xlabel="Processos (P)", ylabel="Speedup", title="Speedup")
ax[1].legend()
ax[2].plot(Ps, eff, "o-", color="#2a9d5c")
ax[2].axhline(1, ls="--", color="gray")
ax[2].set(xlabel="Processos (P)", ylabel="Eficiência", title="Eficiência", ylim=(0, 1.1))
for a in ax[1:]:
    a.set_xticks(Ps)
fig.tight_layout()
save_each(fig, ax, ["strong_tempo.png", "strong_speedup.png", "strong_eficiencia.png"])

# ---------------- Weak ----------------
wd = load(WEAK, "weak")
Pw = np.array(list(wd))
wm = np.array([tmax(wd[p]).mean() for p in Pw])
ws = np.array([tmax(wd[p]).std(ddof=1) if len(wd[p]) > 1 else 0 for p in Pw])
weff = wm[0] / wm
print("\nWEAK: P | Tmax medio | desvio | eficiencia (T1/TP)")
for p, m, s, e in zip(Pw, wm, ws, weff):
    print(f"{p:3d} | {m:9.3f} | {s:7.3f} | {e:6.3f}")

# componentes (media dos Tmax de Tcomp e Tcomm)
comp = np.array([tmax(wd[p], "Tcomp").mean() for p in Pw])
comm = np.array([tmax(wd[p], "Tcomm").mean() for p in Pw])

fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
time_bars(ax[0], wd, Pw, wm, ws, "Tempo (carga por processo constante)", ideal=wm[0],
          xlabel="Processos (P) = imagens")
ax[1].plot(Pw, weff, "o-", color="#2a9d5c")
ax[1].axhline(1, ls="--", color="gray")
ax[1].set(xlabel="Processos (P)", ylabel="Eficiência fraca (T1/TP)", title="Eficiência fraca", ylim=(0, 1.1))
ax[2].bar(Pw.astype(str), comp, color="#2a6fdb", label="Tcomp (Tmax)")
ax[2].bar(Pw.astype(str), comm, bottom=comp, color="#d9534f", label="Tcomm (Tmax)")
ax[2].set(xlabel="Processos (P)", ylabel="Tempo (s)", title="Composição: Tcomp vs Tcomm")
ax[2].legend()
for a in ax[1:2]:
    a.set_xticks(Pw)
fig.tight_layout()
save_each(fig, ax, ["weak_tempo.png", "weak_eficiencia.png", "weak_composicao.png"])
print("\nGerados: strong_{tempo,speedup,eficiencia}.png e weak_{tempo,eficiencia,composicao}.png")
