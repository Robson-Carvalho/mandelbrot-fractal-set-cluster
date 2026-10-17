#!/usr/bin/env python3
"""
analyze.py - tabelas e graficos para as secoes 2.2 a 2.8 do trabalho (Mandelbrot MPI).

Uso:
  python analyze.py --strong DIR [--serial DIR] [--weak DIR] [--out DIR] [--tserial SEG]

Arquivos esperados (em DIR ou subpastas): <prefixo>-P<P>-r<R>.out / .time / .status
  strong : strong-P4-r2.out ...
  weak   : weak-P4-r2.out ... e (opcional) weak-verif-P1-2img-r1.out
  serial : serial-r1.out ...
So entram execucoes com exit=0 e com a linha de resumo no .out.
Desvio entre repeticoes = amostral (n-1). Desvio entre ranks = populacional (como no C).
"""
import argparse
import csv
import glob
import os
import re
import statistics as st
import sys

RE_SUMMARY = re.compile(
    r'^\s*(T\w+)\s*:\s*Tmax=([\d.eE+-]+) s \| Tmin=([\d.eE+-]+) s \| '
    r'Media=([\d.eE+-]+) s \| Desvio=([\d.eE+-]+) s')
RE_RANKHDR = re.compile(r'^Rank (\d+)\s*$')
RE_RANKVAL = re.compile(r'^\s*(Tcomp|Tcomm|Twait|Tgather|Tbar|Ttotal|Tio)\s*=\s*([\d.eE+-]+) s')
RE_TIME = re.compile(r'real=([\d.]+)\s+user=([\d.]+)\s+sys=([\d.]+)')
RE_IMGS = re.compile(r'imagens=(\d+)')
RE_OLD_SERIAL = re.compile(r'Tempo de processamento.*:\s*([\d.]+)')


def mean(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def sdev(xs):
    return st.stdev(xs) if len(xs) >= 2 else 0.0


def read(path):
    try:
        with open(path, errors='replace') as f:
            return f.read()
    except OSError:
        return None


def parse_run(base):
    """base = caminho sem extensao. Retorna dict ou (None, motivo)."""
    out = read(base + '.out')
    if out is None:
        return None, 'sem .out'
    status = read(base + '.status')
    if status is not None and 'exit=0' not in status:
        return None, 'status=' + status.strip()
    run = {'summary': {}, 'ranks': {}, 'tio': 0.0, 'imgs': 1, 'serial_ttotal': None}
    cur = None
    for line in out.splitlines():
        m = RE_SUMMARY.match(line)
        if m:
            k = m.group(1)
            run['summary'][k] = tuple(float(m.group(i)) for i in range(2, 6))
            continue
        m = RE_RANKHDR.match(line)
        if m:
            cur = int(m.group(1))
            run['ranks'].setdefault(cur, {})
            continue
        m = RE_RANKVAL.match(line)
        if m:
            name, val = m.group(1), float(m.group(2))
            if name == 'Tio':
                run['tio'] = val
            elif cur is not None:
                run['ranks'][cur][name] = val
            else:  # formato do serial ("Serial" sem numero de rank)
                run.setdefault('serial_vals', {})[name] = val
            continue
        if line.strip() == 'Serial':
            cur = None
        m = RE_IMGS.search(line)
        if m and 'Resumo' in line:
            run['imgs'] = int(m.group(1))
    # serial no formato novo
    sv = run.get('serial_vals')
    if sv and 'Ttotal' in sv:
        run['serial_ttotal'] = sv['Ttotal']
        if 'Tio' in sv:
            run['tio'] = sv['Tio']
    else:
        m = RE_OLD_SERIAL.search(out)
        if m:
            return None, 'serial no formato ANTIGO (CPU + I/O misturados): nao serve como Tserial'
    if not run['summary'] and run['serial_ttotal'] is None:
        return None, 'sem linha de resumo (execucao incompleta?)'
    tm = read(base + '.time')
    if tm:
        m = RE_TIME.search(tm)
        if m:
            run['real'], run['user'], run['sys'] = (float(m.group(i)) for i in (1, 2, 3))
    return run, None


def load(dirpath, prefix):
    """Retorna {P: [runs]} e lista de avisos."""
    data, warns = {}, []
    if not dirpath:
        return data, warns
    pat = os.path.join(dirpath, '**', prefix + '-P*-r*.out')
    for f in sorted(glob.glob(pat, recursive=True)):
        base = f[:-4]
        m = re.search(re.escape(prefix) + r'-P(\d+)-r(\d+)$', os.path.basename(base))
        if not m:
            continue
        P, r = int(m.group(1)), int(m.group(2))
        run, why = parse_run(base)
        if run is None:
            warns.append(f'{os.path.basename(base)}: ignorada ({why})')
            continue
        run['rep'] = r
        data.setdefault(P, []).append(run)
    return data, warns


def load_serial(dirpath):
    runs, warns = [], []
    if not dirpath:
        return runs, warns
    for f in sorted(glob.glob(os.path.join(dirpath, '**', 'serial-r*.out'), recursive=True)):
        run, why = parse_run(f[:-4])
        if run is None:
            warns.append(f'{os.path.basename(f)}: ignorada ({why})')
        elif run['serial_ttotal'] is not None:
            runs.append(run)
    return runs, warns


def find_pars(*dirs):
    for d in dirs:
        if not d:
            continue
        for f in glob.glob(os.path.join(d, '**', 'env.txt'), recursive=True):
            t = read(f) or ''
            m = re.search(r'^PARS=(.+)$', t, re.M)
            if m:
                return m.group(1).split()
    return None


def amdahl_fit(Ps, S):
    best_f, best_e = 0.0, float('inf')
    for i in range(0, 10001):
        f = i / 10000.0
        e = sum((s - 1.0 / (f + (1 - f) / p)) ** 2 for p, s in zip(Ps, S))
        if e < best_e:
            best_f, best_e = f, e
    return best_f


def amdahl(f, p):
    return 1.0 / (f + (1 - f) / p)


def md_table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join(['---'] * len(headers)) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out)


def f3(x):
    return f'{x:.3f}'


def pct(x):
    return f'{100 * x:.1f}%'


def summ(runs, key, idx):
    """media (entre repeticoes) de um campo do resumo. idx: 0=max 1=min 2=media 3=desvio"""
    return mean([r['summary'][key][idx] for r in runs if key in r['summary']])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--strong', required=True)
    ap.add_argument('--serial')
    ap.add_argument('--weak')
    ap.add_argument('--out', default='analise')
    ap.add_argument('--tserial', type=float, help='Tserial em segundos (se nao houver pasta do serial)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    md = []
    warns = []

    strong, w = load(a.strong, 'strong')
    warns += w
    serial_runs, w = load_serial(a.serial)
    warns += w
    weak, w = load(a.weak, 'weak') if a.weak else ({}, [])
    warns += w
    verif, w = load(a.weak, 'weak-verif') if a.weak else ({}, [])
    warns += w
    weak = {p: v for p, v in weak.items()}

    if not strong:
        print('Nenhuma execucao valida de strong encontrada.'); sys.exit(1)
    Ps = sorted(strong)

    pars = find_pars(a.strong, a.weak)
    pix = None
    if pars and len(pars) >= 2:
        pix = int(pars[0]) * int(pars[1])

    # ---------------- Tserial ----------------
    tserial_note = ''
    if serial_runs:
        ts_vals = [r['serial_ttotal'] for r in serial_runs]
        tserial = mean(ts_vals)
        tserial_note = f'Tserial = {f3(tserial)} s (media de {len(ts_vals)} execucoes, desvio {f3(sdev(ts_vals))} s)'
    elif a.tserial:
        tserial = a.tserial
        tserial_note = f'Tserial = {f3(tserial)} s (informado manualmente)'
    else:
        tserial = mean([r['summary']['Ttotal'][0] for r in strong.get(1, [])]) if 1 in strong else float('nan')
        tserial_note = (f'**ATENCAO:** sem dados do serial; usando o Tmax do MPI com P=1 ({f3(tserial)} s) '
                        'como substituto provisorio. Substitua pelo Tserial medido antes de entregar.')

    md.append('# Resultados\n')
    if pars:
        md.append(f'Parametros: `{" ".join(pars)}`\n')
    md.append(tserial_note + '\n')

    # ---------------- 2.3 strong scaling ----------------
    rows, csv_rows = [], []
    tm_means, S, E = [], [], []
    for P in Ps:
        tmax = [r['summary']['Ttotal'][0] for r in strong[P]]
        m, d = mean(tmax), sdev(tmax)
        tm_means.append(m)
        S.append(tserial / m)
        E.append(tserial / m / P)
    f_amd = amdahl_fit(Ps, S)
    for i, P in enumerate(Ps):
        tmax = [r['summary']['Ttotal'][0] for r in strong[P]]
        rows.append([P, len(tmax), f3(tm_means[i]), f3(sdev(tmax)), f3(S[i]), pct(E[i]),
                     f3(amdahl(f_amd, P))])
        csv_rows.append([P, len(tmax), tm_means[i], sdev(tmax), S[i], E[i], amdahl(f_amd, P)])
    md.append('## 2.3 Strong scaling\n')
    md.append(md_table(['P', 'n', 'Tmax medio (s)', 'desvio (s)', 'Speedup', 'Eficiencia', 'Speedup Amdahl'], rows))
    md.append(f'\nFracao serial efetiva estimada (ajuste de Amdahl por minimos quadrados): '
              f'f = {f_amd:.4f}. Esse f absorve toda perda (comunicacao, desbalanceamento, inicializacao), '
              'nao so codigo estritamente serial.\n')
    with open(os.path.join(a.out, 'strong.csv'), 'w', newline='') as fh:
        w_ = csv.writer(fh)
        w_.writerow(['P', 'n', 'Tmax_medio', 'desvio', 'speedup', 'eficiencia', 'amdahl'])
        w_.writerows(csv_rows)

    # ---------------- 2.2.1 por metrica ----------------
    md.append('## 2.2.1 Medicao interna (MPI_Wtime): estatisticas entre ranks\n')
    md.append('Valores = media das repeticoes do Tmax, Tmin, Tmedia e do desvio entre os P ranks (populacional).\n')
    for key, label in (('Tcomp', 'Tcomp'), ('Tcomm', 'Tcomm'), ('Ttotal', 'Ttotal')):
        rws = []
        for P in Ps:
            rws.append([P, f3(summ(strong[P], key, 0)), f3(summ(strong[P], key, 1)),
                        f3(summ(strong[P], key, 2)), f3(summ(strong[P], key, 3))])
        md.append(f'**{label}**\n')
        md.append(md_table(['P', 'Tmax (s)', 'Tmin (s)', 'Tmedia (s)', 'Desvio (s)'], rws))
        md.append('')

    # ---------------- 2.2.2 externo ----------------
    md.append('## 2.2.2 Medicao externa (`time` do bash) vs. interna\n')
    rws = []
    for P in Ps:
        rs = [r for r in strong[P] if 'real' in r]
        if not rs:
            continue
        ttot = mean([r['summary']['Ttotal'][0] for r in rs])
        tio = mean([r['tio'] for r in rs])
        real = mean([r['real'] for r in rs])
        rws.append([P, f3(ttot), f3(tio), f3(real), f'{mean([r["user"] for r in rs]):.3f}',
                    f'{mean([r["sys"] for r in rs]):.3f}', f3(real - ttot - tio)])
    md.append(md_table(['P', 'Ttotal Tmax (s)', 'Tio rank 0 (s)', 'real (s)', 'user (s)', 'sys (s)',
                        'real - Ttotal - Tio (s)'], rws))
    md.append('\n`user` e `sys` ficam proximos de zero porque o `time` mede o processo `mpirun` (launcher), '
              'e nao os ranks, que rodam em outros processos/nos. A diferenca `real - Ttotal - Tio` e o custo de '
              'lancamento (ssh/mpirun), inicializacao/finalizacao do MPI e alocacao. Para o tempo paralelo, '
              'a referencia e o Tmax do MPI_Wtime.\n')

    # ---------------- 2.5 comunicacao vs computacao ----------------
    md.append('## 2.5 Comunicacao vs computacao\n')
    rws, fc = [], []
    for P in Ps:
        tcomp = summ(strong[P], 'Tcomp', 2)
        tcomm = summ(strong[P], 'Tcomm', 2)
        tcomm_max = summ(strong[P], 'Tcomm', 0)
        ttot_max = summ(strong[P], 'Ttotal', 0)
        tg_max = summ(strong[P], 'Tgather', 0) if any('Tgather' in r['summary'] for r in strong[P]) else float('nan')
        tw_max = summ(strong[P], 'Twait', 0) if any('Twait' in r['summary'] for r in strong[P]) else float('nan')
        fcomm = tcomm_max / ttot_max
        fc.append(fcomm)
        rws.append([P, f3(tcomp), f3(tcomm), pct(fcomm), f3(tw_max), f3(tg_max),
                    pct(tg_max / ttot_max) if tg_max == tg_max else '-'])
    md.append(md_table(['P', 'Tcomp medio (s)', 'Tcomm medio (s)', 'Fcomm = Tcomm_max/Ttotal_max',
                        'Twait max (s)', 'Tgather max (s)', 'Fcomm so transferencia'], rws))
    md.append('\nFcomm oficial inclui espera (Twait) e barreira final, pois o enunciado define Tcomm como todo '
              'tempo dentro de chamadas MPI. A ultima coluna isola a transferencia (Gatherv).\n')

    # ---------------- 2.8 balanceamento ----------------
    md.append('## 2.8 Balanceamento de carga (Tcomp por rank)\n')
    rws = []
    for P in Ps:
        tmax, tmin = summ(strong[P], 'Tcomp', 0), summ(strong[P], 'Tcomp', 1)
        tmed, dsv = summ(strong[P], 'Tcomp', 2), summ(strong[P], 'Tcomp', 3)
        desb = tmax / tmed - 1.0
        classe = 'balanceado' if desb < 0.05 else ('desbalanceamento moderado' if desb < 0.15 else 'desbalanceado')
        rws.append([P, f3(tmax), f3(tmin), f3(tmed), f3(dsv), pct(desb), pct(1 - tmed / tmax), classe])
    md.append(md_table(['P', 'Tmax', 'Tmin', 'Tmedia', 'Desvio', 'Tmax/Tmedia - 1', 'Ociosidade media', 'Classe'], rws))
    md.append('\nCriterio adotado: desbalanceado se Tmax/Tmedia - 1 >= 15%, moderado entre 5% e 15%, balanceado abaixo de 5%. '
              'A ociosidade media (1 - Tmedia/Tmax) e a fracao do tempo do rank mais lento que o rank medio passa esperando.\n')

    # ---------------- weak ----------------
    wk_rows = []
    wPs = sorted(weak)
    if wPs:
        md.append('## 2.4 Weak scaling (N_total = P imagens)\n')
        t1 = mean([r['summary']['Ttotal'][0] for r in weak[1]]) if 1 in weak else float('nan')
        wk_t = []
        for P in wPs:
            tmax = [r['summary']['Ttotal'][0] for r in weak[P]]
            m = mean(tmax)
            wk_t.append(m)
            ef = t1 / m
            ntot = f'{P} x {pix:,} px = {P * pix:,}'.replace(',', '.') if pix else f'{P} imagens'
            wk_rows.append([P, ntot, len(tmax), f3(m), f3(sdev(tmax)), pct(ef), f3(P * ef),
                            pct(summ(weak[P], 'Tcomm', 0) / m)])
        md.append(md_table(['P', 'Ntotal', 'n', 'Tmax medio (s)', 'desvio (s)', 'Eficiencia fraca T1/TP',
                            'Speedup escalado P*T1/TP', 'Fcomm'], wk_rows))
        md.append('')
        if verif and 1 in verif and 1 in weak:
            t2 = mean([r['summary']['Ttotal'][0] for r in verif[1]])
            md.append(f'**Teste de proporcionalidade:** P=1 com 2 imagens = {f3(t2)} s contra {f3(t1)} s com 1 imagem; '
                      f'razao = {t2 / t1:.3f} (ideal: 2,000). Desvios grandes dessa razao indicam que o trabalho nao '
                      'escala exatamente com o numero de imagens.\n')
    elif a.weak:
        md.append('## 2.4 Weak scaling\n\nNenhuma execucao valida encontrada na pasta informada.\n')

    if warns:
        md.append('## Avisos\n')
        md += [f'- {x}' for x in warns]

    with open(os.path.join(a.out, 'resultados.md'), 'w') as fh:
        fh.write('\n'.join(md) + '\n')
    print('\n'.join(md))

    # ---------------- graficos ----------------
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('\n(matplotlib ausente: graficos nao gerados)')
        return

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(Ps, S, 'o-', label='medido')
    ax.plot(Ps, Ps, '--', label='ideal (S = P)')
    pp = list(range(1, max(Ps) + 1))
    ax.plot(pp, [amdahl(f_amd, p) for p in pp], ':', label=f'Amdahl (f = {f_amd:.3f})')
    ax.set_xlabel('P'); ax.set_ylabel('Speedup'); ax.set_title('Strong scaling: speedup')
    ax.grid(alpha=.3); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(a.out, 'speedup.png'), dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(Ps, [100 * e for e in E], 'o-')
    ax.set_xlabel('P'); ax.set_ylabel('Eficiencia (%)'); ax.set_title('Strong scaling: eficiencia')
    ax.set_ylim(0, 110); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(a.out, 'eficiencia.png'), dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4.5))
    comp = [summ(strong[P], 'Tcomp', 2) for P in Ps]
    wait = [summ(strong[P], 'Twait', 2) if any('Twait' in r['summary'] for r in strong[P]) else 0 for P in Ps]
    gat = [summ(strong[P], 'Tgather', 2) if any('Tgather' in r['summary'] for r in strong[P]) else 0 for P in Ps]
    x = list(range(len(Ps)))
    ax.bar(x, comp, label='Tcomp (medio)')
    ax.bar(x, wait, bottom=comp, label='Twait (medio)')
    ax.bar(x, gat, bottom=[c + w_ for c, w_ in zip(comp, wait)], label='Tgather (medio)')
    ax.set_xticks(x); ax.set_xticklabels(Ps)
    ax.set_xlabel('P'); ax.set_ylabel('tempo (s)'); ax.set_title('Composicao do tempo por rank medio')
    ax.legend(); ax.grid(alpha=.3, axis='y')
    fig.tight_layout(); fig.savefig(os.path.join(a.out, 'composicao.png'), dpi=150); plt.close(fig)

    if wPs:
        fig, ax = plt.subplots(figsize=(6, 4.5))
        ax.plot(wPs, wk_t, 'o-', label='medido')
        ax.axhline(wk_t[0], linestyle='--', label='ideal (constante)')
        ax.set_xlabel('P'); ax.set_ylabel('Tmax medio (s)'); ax.set_title('Weak scaling')
        ax.set_ylim(0, max(wk_t) * 1.15); ax.grid(alpha=.3); ax.legend()
        fig.tight_layout(); fig.savefig(os.path.join(a.out, 'weak.png'), dpi=150); plt.close(fig)

    print(f'\nSaidas em: {a.out}/ (resultados.md, strong.csv, *.png)')


if __name__ == '__main__':
    main()