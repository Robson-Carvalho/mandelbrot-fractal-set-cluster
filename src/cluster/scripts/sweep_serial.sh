#!/bin/bash
# uso: REPS=3 PARS="30240 20160 -2 1 -1 1 500" \
#      sweep_serial.sh <dir_app> <binario> <dir_saida> <prefixo>
# Roda o serial no PRIMEIRO no do host_nodes (o mesmo onde roda o rank 0 do MPI).
APP_DIR=$1; BIN=$2; OUT=$3; PREFIX=$4
REPS=${REPS:-3}
TIMEOUT=${TIMEOUT:-3600}
HOSTFILE=${HOSTFILE:-$HOME/cluster/host_nodes}
NODE=$(awk 'NF{print $1; exit}' "$HOSTFILE")

mkdir -p "$OUT"

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$NODE" "test -x $APP_DIR/$BIN" < /dev/null; then
  echo "ERRO: no $NODE inacessivel por ssh ou sem o binario $APP_DIR/$BIN" | tee "$OUT/ERRO.txt"
  exit 1
fi

{ date; echo "NODE=$NODE"; echo "PARS=$PARS"; ssh -o BatchMode=yes "$NODE" "lscpu | head -20; free -m" < /dev/null; } > "$OUT/env.txt"

TIMEFORMAT='real=%R user=%U sys=%S'

for R in $(seq 1 "$REPS"); do
  TAG="$PREFIX-r$R"
  echo "$(date +%T) iniciando $TAG" >> "$OUT/progresso.txt"
  { time timeout "$TIMEOUT" ssh -o BatchMode=yes "$NODE" \
      "cd $APP_DIR && ./$BIN $PARS /tmp/$TAG.ppm; rc=\$?; rm -f /tmp/$TAG.ppm; exit \$rc" \
      > "$OUT/$TAG.out" 2>&1 < /dev/null ; } 2> "$OUT/$TAG.time"
  RC=$?
  echo "exit=$RC" > "$OUT/$TAG.status"
  if [ "$RC" -eq 124 ]; then
    ssh -o BatchMode=yes "$NODE" "pkill -9 $BIN" < /dev/null 2>/dev/null
  fi
done
echo "FIM $(date)" > "$OUT/DONE"