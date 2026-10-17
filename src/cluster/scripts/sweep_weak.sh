#!/bin/bash
# uso: PROCS="1 2 4 8 12" REPS=3 PARS="15120 10080 -2 1 -1 1 1500" \
#      sweep_weak.sh <dir_app> <binario> <dir_saida> <prefixo>
# Weak scaling: imagem fixa (PARS) gerada P vezes em sequencia (num_imagens = P). Nao grava imagem.
APP_DIR=$1; BIN=$2; OUT=$3; PREFIX=$4
PROCS=${PROCS:-"1 2 4 8 12"}
REPS=${REPS:-3}
VERIFY_REPS=${VERIFY_REPS:-1}      # repeticoes do teste de proporcionalidade (P=1, 2 imagens); 0 desliga
HOSTFILE=${HOSTFILE:-$HOME/cluster/host_nodes}
TIMEOUT=${TIMEOUT:-3600}
TIMEFORMAT='real=%R user=%U sys=%S'

cd "$APP_DIR" || exit 1
mkdir -p "$OUT"

MAXP=$(for p in $PROCS; do echo $p; done | sort -n | tail -1)
TOTAL_SLOTS=$(sed -n 's/.*slots=\([0-9]*\).*/\1/p' "$HOSTFILE" | awk '{s+=$1} END{print s}')
if [ "$MAXP" -gt "$TOTAL_SLOTS" ]; then
  echo "ERRO: P=$MAXP maior que slots ($TOTAL_SLOTS)" | tee "$OUT/ERRO.txt"; exit 1
fi
for NODE in $(awk 'NF{print $1}' "$HOSTFILE" | head -n "$MAXP"); do
  if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$NODE" "test -x $APP_DIR/$BIN" < /dev/null; then
    echo "ERRO: no $NODE inacessivel por ssh ou sem o binario $APP_DIR/$BIN" | tee "$OUT/ERRO.txt"; exit 1
  fi
done

{ date; echo "PARS=$PARS"; echo "PROCS=$PROCS"; echo "MODO=weak (num_imagens = P)"; mpirun --version | head -1; cat "$HOSTFILE"; lscpu | head -20; } > "$OUT/env.txt"

# roda_um <tag> <P> <num_imagens>
roda_um() {
  local TAG=$1 P=$2 NIMG=$3
  echo "$(date +%T) iniciando $TAG (P=$P, imagens=$NIMG)" >> "$OUT/progresso.txt"
  { time timeout "$TIMEOUT" mpirun -np "$P" -machinefile "$HOSTFILE" ./"$BIN" $PARS "-" "$NIMG" \
      > "$OUT/$TAG.out" 2>&1 < /dev/null ; } 2> "$OUT/$TAG.time"
  local RC=$?
  echo "exit=$RC" > "$OUT/$TAG.status"
  if [ "$RC" -eq 124 ]; then
    pkill -9 mpirun
    for NODE in $(awk 'NF{print $1}' "$HOSTFILE" | head -n "$P"); do
      ssh -o BatchMode=yes "$NODE" "pkill -9 $BIN" < /dev/null 2>/dev/null
    done
  fi
}

# Teste de proporcionalidade: P=1 com 2 imagens deve levar ~2x o P=1 com 1 imagem
for R in $(seq 1 "$VERIFY_REPS"); do
  [ "$VERIFY_REPS" -gt 0 ] && roda_um "$PREFIX-verif-P1-2img-r$R" 1 2
done

for P in $PROCS; do
  for R in $(seq 1 "$REPS"); do
    roda_um "$PREFIX-P$P-r$R" "$P" "$P"
  done
done
echo "FIM $(date)" > "$OUT/DONE"