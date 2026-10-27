#!/usr/bin/env python3
"""Compara os dois algoritmos (balanceado x SPMD sem balanceamento) com graficos.

Comparacoes (dois algoritmos) vao para --out; tabelas de cada algoritmo, para a pasta dele.

Uso: python compare_scaling.py --notes src/notes [--out src/notes/analise]
Le a execucao COMPLETA mais recente (DONE + P=1) de strong-*/weak-* em
<notes>/mandelbrot e <notes>/mandelbrot_spmd. Metrica: Tmax entre ranks (MPI_Wtime).
"""
import argparse
import glob
import os
import re
import sys
import textwrap
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

# ---- 2.5 Fracao de comunicacao: Fcomm = Tcomm_max / Ttotal_max ----
def fcomm(d):
    Ps = np.array(list(d))
    return Ps, np.array([np.mean([r["Tcomm"][0] / r["Ttotal"][0] for r in d[p]]) for p in Ps]) * 100


for kind, i, title, name in [("strong", 0, "Strong scaling", "comparacao_strong_fcomm.png"),
                             ("weak", 1, "Weak scaling", "comparacao_weak_fcomm.png")]:
    fig, ax = new(f"{title}: fração de comunicação", ylabel="% do tempo total gasto em comunicação")
    for a in ALGS:
        Ps, y = fcomm(DATA[a][i])
        line(ax, a, Ps, y)
    ax.set_ylim(0, None)
    finish(fig, ax, name, Ps)


# ---- Tabelas como imagem ----
PIXELS_PER_IMAGE = 15120 * 10080  # STRONG/WEAK_PARS do Makefile: largura x altura por imagem


def table_image(rows, cols, title, name, outdir):
    """Tabela grande e legivel (slides/relatorio): fonte 16, cabecalho quebrado em linhas."""
    cols = [c if "\n" in c else textwrap.fill(c, 13) for c in cols]
    n_rows = len(rows)
    head_units = 1.7  # cabecalho ocupa mais altura (ate 3 linhas)
    row_h = 0.75      # polegadas por linha de dados
    fig_w = max(10, 2.7 * len(cols))
    fig_h = row_h * (n_rows + head_units) + 1.3
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_title(textwrap.fill(title, 70), fontsize=19, fontweight="bold", pad=18)
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center", bbox=[0, 0, 1, 1])
    t.auto_set_font_size(False)
    t.set_fontsize(17)
    total = n_rows + head_units
    for (r, c), cell in t.get_celld().items():
        cell.set_height((head_units if r == 0 else 1) / total)
        cell.set_edgecolor("#bbbbbb")
        cell.set_linewidth(1.2)
        if r == 0:
            cell.set_facecolor("#2a3f5f")
            cell.set_text_props(color="white", fontweight="bold", fontsize=16)
        elif r % 2 == 0:
            cell.set_facecolor("#eef2f8")
    fig.savefig(os.path.join(outdir, name), bbox_inches="tight", dpi=200)
    plt.close(fig)


def sd(v):
    return float(np.std(v, ddof=1)) if len(v) > 1 else 0.0


for a, (lab, _, _) in ALGS.items():
    strong, weak = DATA[a]
    adir = os.path.join(NOTES, a)  # tabelas de cada algoritmo ficam na pasta dele

    # 2.3 Strong
    t1 = np.mean([r["Ttotal"][0] for r in strong[min(strong)]])
    rows = []
    for p, runs in strong.items():
        v = [r["Ttotal"][0] for r in runs]
        rows.append([p, f"{np.mean(v):.3f}", f"{sd(v):.3f}", f"{t1 / np.mean(v):.3f}", f"{t1 / np.mean(v) / p:.3f}"])
    table_image(rows, ["P", "Tmax médio (s)", "Desvio (s)", "Speedup", "Eficiência"],
                f"Strong scaling – {lab}", "tabela_strong.png", adir)

    # 2.4 Weak
    t1 = np.mean([r["Ttotal"][0] for r in weak[min(weak)]])
    rows = []
    for p, runs in weak.items():
        v = [r["Ttotal"][0] for r in runs]
        rows.append([p, f"{p} imagens ({p * PIXELS_PER_IMAGE / 1e6:,.0f} Mpx)", f"{np.mean(v):.3f}",
                     f"{sd(v):.3f}", f"{t1 / np.mean(v):.3f}"])
    table_image(rows, ["P", "Ntotal", "Tmax médio (s)", "Desvio (s)", "Eficiência fraca"],
                f"Weak scaling – {lab}", "tabela_weak.png", adir)

    # 2.5 Comunicacao vs computacao (strong e weak)
    for kind, d in (("strong", strong), ("weak", weak)):
        rows = []
        for p, runs in d.items():
            comp = np.mean([r["Tcomp"][2] for r in runs])
            comm = np.mean([r["Tcomm"][2] for r in runs])
            fc = np.mean([r["Tcomm"][0] / r["Ttotal"][0] for r in runs]) * 100
            rows.append([p, f"{comp:.3f}", f"{comm:.3f}", f"{fc:.2f}"])
        table_image(rows, ["P", "Tcomp médio (s)", "Tcomm médio (s)", "% do tempo em\ncomunicação"],
                    f"Comunicação vs computação ({kind}) – {lab}", f"tabela_{kind}_fcomm.png", adir)

    # 2.2.1 Estatistica entre ranks (media das execucoes) - strong e weak
    for kind, d, kname in [("strong", strong, "Strong"), ("weak", weak, "Weak")]:
        rows = []
        for p, runs in d.items():
            for m in ("Tcomp", "Tcomm", "Ttotal"):
                vals = [np.mean([r[m][k] for r in runs]) for k in range(4)]
                rows.append([p, m] + [f"{x:.3f}" for x in vals])
        table_image(rows, ["P", "Métrica", "Tmax (s)", "Tmin (s)", "Tmédia (s)", "Desvio (s)"],
                    f"Estatísticas entre ranks ({kname}, média das execuções) – {lab}", f"tabela_ranks_{kind}.png", adir)

# ---- 2.8 Comparativo de Carga por Rank (P=12 Strong Scaling) ----
def parse_per_rank_tcomp(filepath):
    """Extrai Tcomp de cada rank individual de um arquivo .out."""
    ranks = {}
    cur_rank = None
    with open(filepath, errors="replace") as fh:
        for line in fh:
            m_rank = re.match(r"^Rank\s+(\d+)", line)
            if m_rank:
                cur_rank = int(m_rank.group(1))
            elif cur_rank is not None:
                m_tc = re.match(r"^\s*Tcomp\s*=\s*([\d.]+)", line)
                if m_tc:
                    ranks[cur_rank] = float(m_tc.group(1))
                    cur_rank = None
    return ranks

fig, ax = plt.subplots(figsize=(8, 4.8))
r_opt = parse_per_rank_tcomp(os.path.join(latest(os.path.join(NOTES, "mandelbrot"), "strong"), "strong-P12-r1.out"))
r_spmd = parse_per_rank_tcomp(os.path.join(latest(os.path.join(NOTES, "mandelbrot_spmd"), "strong"), "strong-P12-r1.out"))
if r_opt and r_spmd:
    ranks_idx = sorted(set(r_opt.keys()) | set(r_spmd.keys()))
    w = 0.38
    x = np.arange(len(ranks_idx))
    ax.bar(x - w/2, [r_opt.get(k, 0) for k in ranks_idx], width=w, color="#2a6fdb", label="Balanceado (mandelbrot)")
    ax.bar(x + w/2, [r_spmd.get(k, 0) for k in ranks_idx], width=w, color="#d9534f", label="Sem balanceamento (SPMD)")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Rank {k}" for k in ranks_idx], rotation=45)
    ax.set_ylabel("Tcomp individual (s)")
    ax.set_title("2.8 Distribuição de Carga por Rank (P=12, Strong Scaling)", fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "comparacao_distribuicao_ranks_P12.png"), dpi=200)
    plt.close(fig)

# ---- 2.10 Original (SPMD ingenuo) x Otimizado (mandelbrot balanceado) ----
IMG_BYTES = 15120 * 10080 * 3  # bytes de uma imagem (RGB), igual ao global_buffer do rank 0


def optimization_table(i, kind, title):
    orig, opt = DATA["mandelbrot_spmd"][i], DATA["mandelbrot"][i]
    rows = []
    for p in sorted(set(orig) & set(opt)):
        to = np.mean([r["Ttotal"][0] for r in orig[p]])
        tp = np.mean([r["Ttotal"][0] for r in opt[p]])
        fo = np.mean([r["Tcomm"][0] / r["Ttotal"][0] for r in orig[p]]) * 100
        fp = np.mean([r["Tcomm"][0] / r["Ttotal"][0] for r in opt[p]]) * 100
        imgs = p if kind == "weak" else 1
        vol = imgs * IMG_BYTES * (p - 1) / p / 1e6  # Gatherv: tudo exceto a parte do proprio rank 0
        rows.append([p, f"{to:.2f}", f"{tp:.2f}", f"{to / tp:.2f}x", f"{fo:.1f}", f"{fp:.1f}", f"{vol:,.0f}"])
    table_image(rows, ["P", "Original SPMD\nTmax (s)", "Otimizado\nTmax (s)", "Speedup\notimização",
                       "% comunicação\noriginal", "% comunicação\notimizado", "Volume Gatherv\n(MB, ambos)"],
                title, f"tabela_otimizacao_{kind}.png", OUT)


optimization_table(0, "strong", "Original (SPMD) x Otimizado (mandelbrot balanceado) – strong scaling")
optimization_table(1, "weak", "Original (SPMD) x Otimizado (mandelbrot balanceado) – weak scaling")

print(f"\nComparacoes salvas em {OUT}; tabelas em <notes>/<algoritmo>/")
