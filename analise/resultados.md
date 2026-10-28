# Resultados

Parametros: `15120 10080 -2 1 -1 1 1500`

**ATENCAO:** sem dados do serial; usando o Tmax do MPI com P=1 (224.250 s) como substituto provisorio. Substitua pelo Tserial medido antes de entregar.

## 2.3 Strong scaling (Lei de Amdahl)

| P | n | Tmax medio (s) | desvio (s) | Speedup | Eficiencia | Speedup Amdahl |
|---|---|---|---|---|---|---|
| 1 | 3 | 224.250 | 0.004 | 1.000 | 100.0% | 1.000 |
| 2 | 3 | 114.306 | 0.236 | 1.962 | 98.1% | 1.767 |
| 4 | 3 | 95.361 | 0.004 | 2.352 | 58.8% | 2.866 |
| 8 | 3 | 59.339 | 0.118 | 3.779 | 47.2% | 4.159 |
| 12 | 3 | 42.413 | 0.117 | 5.287 | 44.1% | 4.895 |

Fracao serial efetiva estimada (ajuste de Amdahl por minimos quadrados): f = 0.1319 (speedup maximo assintotico 1/f = 7.58x se f > 0). Esse f absorve toda perda (comunicacao, desbalanceamento, sincronizacao), nao so codigo estritamente serial.

## 2.2.1 Medicao interna (MPI_Wtime): estatisticas entre ranks

Valores = media das repeticoes do Tmax, Tmin, Tmedia e do desvio entre os P ranks (populacional).

**Tcomp**

| P | Tmax (s) | Tmin (s) | Tmedia (s) | Desvio (s) |
|---|---|---|---|---|
| 1 | 224.250 | 224.250 | 224.250 | 0.000 |
| 2 | 112.159 | 112.098 | 112.129 | 0.031 |
| 4 | 92.397 | 19.740 | 56.066 | 36.311 |
| 8 | 55.823 | 2.884 | 28.032 | 20.007 |
| 12 | 38.727 | 0.679 | 18.690 | 13.557 |

**Tcomm**

| P | Tmax (s) | Tmin (s) | Tmedia (s) | Desvio (s) |
|---|---|---|---|---|
| 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| 2 | 2.208 | 2.146 | 2.177 | 0.031 |
| 4 | 75.621 | 2.962 | 39.294 | 36.311 |
| 8 | 56.456 | 3.516 | 31.306 | 20.008 |
| 12 | 41.733 | 3.685 | 23.722 | 13.556 |

**Ttotal**

| P | Tmax (s) | Tmin (s) | Tmedia (s) | Desvio (s) |
|---|---|---|---|---|
| 1 | 224.250 | 224.250 | 224.250 | 0.000 |
| 2 | 114.306 | 114.305 | 114.306 | 0.001 |
| 4 | 95.361 | 95.359 | 95.360 | 0.001 |
| 8 | 59.339 | 59.338 | 59.339 | 0.000 |
| 12 | 42.413 | 42.411 | 42.412 | 0.001 |

## 2.2.2 Medicao externa (`time` do bash) vs. interna

| P | Ttotal Tmax (s) | Tio rank 0 (s) | real (s) | user (s) | sys (s) | real - Ttotal - Tio (s) |
|---|---|---|---|---|---|---|
| 1 | 224.250 | 5.539 | 231.897 | 0.021 | 0.031 | 2.109 |
| 2 | 114.306 | 6.319 | 122.659 | 0.021 | 0.031 | 2.034 |
| 4 | 95.361 | 5.873 | 103.152 | 0.023 | 0.031 | 1.919 |
| 8 | 59.339 | 5.594 | 66.835 | 0.023 | 0.031 | 1.902 |
| 12 | 42.413 | 5.622 | 49.946 | 0.026 | 0.029 | 1.910 |

`user` e `sys` ficam proximos de zero porque o `time` mede o processo `mpirun` (launcher), e nao os ranks, que rodam em outros processos/nos. A diferenca `real - Ttotal - Tio` e o custo de lancamento (ssh/mpirun), inicializacao/finalizacao do MPI e alocacao. Para o tempo paralelo, a referencia e o Tmax do MPI_Wtime.

## 2.5 Comunicacao vs computacao

| P | Tcomp medio (s) | Tcomm medio (s) | Fcomm = Tcomm_max/Ttotal_max | Twait max (s) | Tgather max (s) | Fcomm so transferencia |
|---|---|---|---|---|---|---|
| 1 | 224.250 | 0.000 | 0.0% | 0.000 | 0.000 | 0.0% |
| 2 | 112.129 | 2.177 | 1.9% | 0.063 | 2.145 | 1.9% |
| 4 | 56.066 | 39.294 | 79.3% | 72.659 | 2.962 | 3.1% |
| 8 | 28.032 | 31.306 | 95.1% | 52.940 | 3.516 | 5.9% |
| 12 | 18.690 | 23.722 | 98.4% | 38.049 | 3.684 | 8.7% |

Fcomm oficial inclui espera (Twait) e barreira final, pois o enunciado define Tcomm como todo tempo dentro de chamadas MPI. A ultima coluna isola a transferencia (Gatherv).

## 2.8 Balanceamento de carga (Tcomp por rank)

| P | Tmax | Tmin | Tmedia | Desvio | Tmax/Tmedia - 1 | Ociosidade media | Classe |
|---|---|---|---|---|---|---|---|
| 1 | 224.250 | 224.250 | 224.250 | 0.000 | 0.0% | 0.0% | balanceado |
| 2 | 112.159 | 112.098 | 112.129 | 0.031 | 0.0% | 0.0% | balanceado |
| 4 | 92.397 | 19.740 | 56.066 | 36.311 | 64.8% | 39.3% | desbalanceado |
| 8 | 55.823 | 2.884 | 28.032 | 20.007 | 99.1% | 49.8% | desbalanceado |
| 12 | 38.727 | 0.679 | 18.690 | 13.557 | 107.2% | 51.7% | desbalanceado |

Criterio adotado: desbalanceado se Tmax/Tmedia - 1 >= 15%, moderado entre 5% e 15%, balanceado abaixo de 5%. A ociosidade media (1 - Tmedia/Tmax) e a fracao do tempo do rank mais lento que o rank medio passa esperando.

## 2.4 Weak scaling e Lei de Gustafson (N_total = P imagens)

| P | Ntotal | n | Tmax medio (s) | desvio (s) | Eficiencia fraca (T1/TP) | Speedup Escalado (P*T1/TP) | Gustafson (s=Fcomm) | Gustafson ajuste (s=0.5857) | Fcomm |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 x 152.409.600 px = 152.409.600 | 3 | 224.253 | 0.001 | 100.0% | 1.000 | 1.000 | 1.000 | 0.0% |
| 2 | 2 x 152.409.600 px = 304.819.200 | 3 | 228.336 | 0.008 | 98.2% | 1.964 | 1.982 | 1.414 | 1.8% |
| 4 | 4 x 152.409.600 px = 609.638.400 | 3 | 378.457 | 0.016 | 59.3% | 2.370 | 1.626 | 2.243 | 79.1% |
| 8 | 8 x 152.409.600 px = 1.219.276.800 | 3 | 463.734 | 0.011 | 48.4% | 3.869 | 1.348 | 3.900 | 95.0% |
| 12 | 12 x 152.409.600 px = 1.828.915.200 | 3 | 489.964 | 0.099 | 45.8% | 5.492 | 1.183 | 5.557 | 98.3% |

Pela **Lei de Gustafson**, $S_G(P) = P + (1 - P)s$. Tomando $s = F_{\text{comm}}(P)$ tem-se a estimativa baseada na fracao de comunicacao medida em cada $P$; ajustando $s$ por minimos quadrados sobre a curva empirica $P \cdot (T_1/T_P)$, obtem-se $s = 0.5857$.

**Teste de proporcionalidade:** P=1 com 2 imagens = 448.507 s contra 224.253 s com 1 imagem; razao = 2.000 (ideal: 2.000). Desvios grandes dessa razao indicam que o trabalho nao escala exatamente com o numero de imagens.

