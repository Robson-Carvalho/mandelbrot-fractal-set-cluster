APP_DIR=$1; BIN=$2; OUT=$3; PREFIX=$4
PROCS=${PROCS:-"1 2 4 8 12"}
REPS=${REPS:-3}
HOSTFILE=${HOSTFILE:-$HOME/cluster/host_nodes}
TIMEOUT=${TIMEOUT:-3600}
TIMEFORMAT='real=%R user=%U sys=%S'
NODE0=$(awk 'NF{print $1; exit}' "$HOSTFILE")

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

{ date; echo "PARS=$PARS"; echo "PROCS=$PROCS"; mpirun --version | head -1; cat "$HOSTFILE"; lscpu | head -20; } > "$OUT/env.txt"

for P in $PROCS; do
  for R in $(seq 1 "$REPS"); do
    TAG="$PREFIX-P$P-r$R"
    echo "$(date +%T) iniciando $TAG" >> "$OUT/progresso.txt"

    { time timeout "$TIMEOUT" mpirun -np "$P" -machinefile "$HOSTFILE" ./"$BIN" $PARS "/tmp/$TAG.ppm" \
        > "$OUT/$TAG.out" 2>&1 < /dev/null ; } 2> "$OUT/$TAG.time"
    RC=$?
    echo "exit=$RC" > "$OUT/$TAG.status"

    if [ "$RC" -eq 124 ]; then
      pkill -9 mpirun
      for NODE in $(awk 'NF{print $1}' "$HOSTFILE" | head -n "$P"); do
        ssh -o BatchMode=yes "$NODE" "pkill -9 $BIN" < /dev/null 2>/dev/null
      done
    fi

    ssh -o BatchMode=yes "$NODE0" "rm -f /tmp/$TAG.ppm" < /dev/null
  done
done
echo "FIM $(date)" > "$OUT/DONE"