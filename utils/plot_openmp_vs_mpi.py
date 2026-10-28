#!/usr/bin/env python3
"""Gera imagem da tabela comparativa OpenMP vs MPI no estilo academico (booktabs/LaTeX).

Uso: python utils/plot_openmp_vs_mpi.py [--out src/notes/analise]
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="src/notes/analise", help="Diretório de saída")
args = ap.parse_args()

outdir = os.path.abspath(args.out)
os.makedirs(outdir, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "serif"],
    "mathtext.fontset": "cm",
    "figure.facecolor": "white",
})

cols = ["Critério", "OpenMP (Compartilhada)", "MPI (Distribuída)"]

rows = [
    ["Modelo de memória", "Compartilhada (RAM global)", "Distribuída (privada por rank)"],
    ["Escopo de execução", "Intra-nó (núcleos de um host)", "Inter-nó (múltiplos nós em cluster)"],
    ["Custo de criação", "Baixo (threads leves)", "Alto (processos pesados do SO)"],
    ["Comunicação", "Acesso direto à memória", "Passagem de mensagens explícita"],
    ["Latência relativa", "Muito baixa (ordem de ns)", "Média/Alta (ordem de µs a ms)"],
    ["Escalabilidade típica", "Limitada ao nó (cores locais)", "Alta (milhares de nós/processos)"],
    ["Estilo de código", "Diretivas (#pragma omp)", "Chamadas de biblioteca"],
]

n_rows = len(rows)

fig, ax = plt.subplots(figsize=(10.5, 3.2), dpi=220)
ax.axis("off")

table = ax.table(
    cellText=rows,
    colLabels=cols,
    loc="center",
    cellLoc="left",
    colWidths=[0.22, 0.39, 0.39],
    bbox=[0, 0, 1, 1]
)

table.auto_set_font_size(False)
table.set_fontsize(10.5)

# Estilo Booktabs (LaTeX): linhas horizontais apenas no topo, abaixo do cabeçalho e na base
for (r, c), cell in table.get_celld().items():
    cell.set_facecolor("white")
    cell.set_edgecolor("black")
    
    if r == 0:
        # Cabeçalho: linha superior mais grossa, linha inferior normal
        cell.visible_edges = "TB"
        cell.set_linewidth(1.3)
        cell.set_text_props(weight="bold", color="black", fontsize=11)
    elif r == n_rows:
        # Última linha: linha inferior
        cell.visible_edges = "B"
        cell.set_linewidth(1.3)
        cell.set_text_props(color="#111111")
    else:
        # Linhas do corpo: sem bordas
        cell.visible_edges = ""
        cell.set_text_props(color="#111111")
    
    # Destaque suave na primeira coluna (Critério)
    if c == 0 and r > 0:
        cell.set_text_props(weight="bold", color="#111111")

output_file = os.path.join(outdir, "tabela_openmp_vs_mpi.png")
fig.savefig(output_file, bbox_inches="tight", dpi=220, facecolor="white")
plt.close(fig)

print(f"Tabela no padrao academico gerada com sucesso: {output_file}")
