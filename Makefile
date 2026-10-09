include config.mk

HOST ?= $(IP)
LOCAL_DIR := src/cluster
REMOTE_DIR := ~/cluster

LOCAL_HELLO_DIR := $(LOCAL_DIR)/hello
REMOTE_HELLO_DIR := $(REMOTE_DIR)/hello

LOCAL_MPI_DIR := $(LOCAL_DIR)/mpi
REMOTE_MPI_DIR := $(REMOTE_DIR)/mpi

LOCAL_NOTES_DIR := src/notes
REMOTE_NOTES_DIR := ~/notes
REMOTE_HELLO_NOTES_DIR := $(REMOTE_NOTES_DIR)/hello
REMOTE_MPI_NOTES_DIR := $(REMOTE_NOTES_DIR)/mpi
REMOTE_SERIAL_NOTES_DIR := $(REMOTE_NOTES_DIR)/serial

LOCAL_SERIAL_DIR := $(LOCAL_DIR)/serial
REMOTE_SERIAL_DIR := $(REMOTE_DIR)/serial

LOCAL_PICTURES_DIR := src/pictures
REMOTE_PICTURES_DIR := ~/pictures

REMOTE_MANDELBROT_DIR := $(REMOTE_MPI_DIR)/mandelbrot
REMOTE_MANDELBROT_NOTES_DIR := $(REMOTE_NOTES_DIR)/mandelbrot
REMOTE_MANDELBROT_PICTURES_DIR := $(REMOTE_PICTURES_DIR)/mandelbrot

REMOTE_SERIAL_PICTURES_DIR := $(REMOTE_PICTURES_DIR)/serial

REMOTE_SPMD_DIR := $(REMOTE_MPI_DIR)/mandelbrot_spmd
REMOTE_SPMD_NOTES_DIR := $(REMOTE_NOTES_DIR)/mandelbrot_spmd

HOST_FILE ?= host_nodes
REMOTE_HOST_FILE := $(REMOTE_DIR)/host_nodes
NP ?= 4
PARS ?=

RUN_ID := $(shell date +%Y%m%d-%H%M%S)

ifneq ($(PASSWORD),)
    SSH_CMD := sshpass -p '$(PASSWORD)' ssh
    SCP_CMD := sshpass -p '$(PASSWORD)' scp
else
    SSH_CMD := ssh
    SCP_CMD := scp
endif

.PHONY: help hello-cluster sync-cluster build-hello run-hello sync-notes sync-pictures clean-pictures clean-notes-hello all-hello build-mpi run-mpi all-mpi clean-notes-mpi build-mandelbrot run-mandelbrot clean-notes-mandelbrot all-mandelbrot check-mandelbrot stop-mandelbrot build-serial run-serial check-serial clean-notes-serial all-serial

help: ## Exibe esta mensagem de ajuda
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

all-hello: sync-cluster build-hello run-hello ## Sincroniza, compila e executa o hello (Padrão)

all-mpi: sync-cluster build-mpi run-mpi ## Sincroniza, compila e executa o hello_mpi (MPI)

all-mandelbrot: sync-cluster build-mandelbrot run-mandelbrot ## Sincroniza, compila e executa o mandelbrot

all-spmd: sync-cluster build-spmd run-spmd ## Sincroniza, compila e executa o mandelbrot_spmd (ingênuo)

all-serial: sync-cluster build-serial run-serial ## Sincroniza, compila e executa o serial

### Padrão

hello-cluster: ## Testa a conexão executando hello no cluster
	@echo "Conectando em $(USER)@$(HOST)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "cd $(REMOTE_HELLO_DIR) && ./main; exit"

build-hello: ## Compila o programa hello
	@echo "Compilando hello com -O2"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_HELLO_DIR) && cd $(REMOTE_HELLO_DIR) && gcc -O2 main.c -o main"

run-hello: ## Executa o programa hello e salva as métricas
	@echo "Executando hello e salvando em $(REMOTE_HELLO_NOTES_DIR)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_HELLO_NOTES_DIR) && cd $(REMOTE_HELLO_DIR) && ( (time ./main > $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).out) 2> $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).time ) || ( rm -f $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).out $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).time && false )"

sync-cluster: ## Envia todos os arquivos locais para o cluster remoto
	@echo "Removendo e substituindo $(REMOTE_DIR) em $(USER)@$(HOST)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_DIR)"
	$(SCP_CMD) -r -P $(shell echo $(ARGS) | tr -d -c 0-9) $(LOCAL_DIR) $(USER)@$(HOST):$(REMOTE_DIR)
	$(SCP_CMD) -P $(shell echo $(ARGS) | tr -d -c 0-9) $(HOST_FILE) $(USER)@$(HOST):$(REMOTE_HOST_FILE)

sync-notes: ## Baixa os logs e relatórios remotos para o diretório local
	@echo "Baixando $(REMOTE_NOTES_DIR) de $(USER)@$(HOST) para $(LOCAL_NOTES_DIR)"
	mkdir -p $(LOCAL_NOTES_DIR)
	$(SCP_CMD) -r -P $(shell echo $(ARGS) | tr -d -c 0-9) $(USER)@$(HOST):$(REMOTE_NOTES_DIR)/. $(LOCAL_NOTES_DIR)/

sync-pictures: ## Baixa as imagens remotas compactadas para o diretório local
	@echo "Compactando e baixando $(REMOTE_PICTURES_DIR) de $(USER)@$(HOST) para $(LOCAL_PICTURES_DIR)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "cd ~ && if [ -d pictures ]; then python3 -c \"import tarfile; t = tarfile.open('pictures_sync.tar.gz', 'w:gz'); t.add('pictures'); t.close()\"; fi"
	mkdir -p src
	$(SCP_CMD) -P $(shell echo $(ARGS) | tr -d -c 0-9) $(USER)@$(HOST):~/pictures_sync.tar.gz ./ || true
	if [ -f pictures_sync.tar.gz ]; then tar -xzf pictures_sync.tar.gz -C src/; rm -f pictures_sync.tar.gz; fi
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -f ~/pictures_sync.tar.gz"

clean-pictures: ## Apaga as imagens na VPS e localmente
	@echo "Limpando diretório de imagens na VPS e localmente"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_PICTURES_DIR)"
	rm -rf $(LOCAL_PICTURES_DIR)

clean-notes-hello: ## Apaga os resultados do hello (local e VPS)
	@echo "Limpando análises do hello na VPS e localmente"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_HELLO_NOTES_DIR)"
	rm -rf $(LOCAL_NOTES_DIR)/hello


### MPI

build-mpi: ## Compila o hello_mpi com mpicc
	@echo "Compilando hello_mpi com mpicc"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_MPI_DIR) && cd $(REMOTE_MPI_DIR) && mpicc -O2 hello_mpi.c -o hello_mpi"

run-mpi: ## Executa o hello_mpi em background no cluster
	@echo "Executando hello_mpi no cluster com nohup em background"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_MPI_NOTES_DIR) && cd $(REMOTE_MPI_DIR) && nohup mpirun -np $(NP) -machinefile $(REMOTE_HOST_FILE) ./hello_mpi $(PARS) > $(REMOTE_MPI_NOTES_DIR)/mpi-$(RUN_ID).log 2>&1 &"

clean-notes-mpi: ## Apaga os resultados do hello_mpi (local e VPS)
	@echo "Limpando análises do mpi na VPS e localmente"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_MPI_NOTES_DIR)"
	rm -rf $(LOCAL_NOTES_DIR)/mpi

### Mandelbrot

build-mandelbrot: ## Compila o mandelbrot com mpicc
	@echo "Compilando mandelbrot com mpicc"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "cd $(REMOTE_MANDELBROT_DIR) && mpicc -O2 main.c lib/complex.c lib/mandelbrot.c -o mandelbrot -lm"

run-mandelbrot: ## Executa o mandelbrot em background no cluster
	@echo "Executando mandelbrot no cluster com nohup em background"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_MANDELBROT_NOTES_DIR) && mkdir -p $(REMOTE_MANDELBROT_PICTURES_DIR) && cd $(REMOTE_MANDELBROT_DIR) && echo 'nohup mpirun -np $(NP) -machinefile $(REMOTE_HOST_FILE) ./mandelbrot $(PARS) $(REMOTE_MANDELBROT_PICTURES_DIR)/mandelbrot-$(RUN_ID).ppm > $(REMOTE_MANDELBROT_NOTES_DIR)/mandelbrot-$(RUN_ID).log 2>&1 < /dev/null &' > run_bg.sh && bash run_bg.sh"

check-mandelbrot: ## Checa se o mandelbrot está rodando no cluster
	@echo "Verificando status do processo no cluster..."
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "pgrep -f '[m]pirun.*mandelbrot' > /dev/null && echo '🟢 Algoritmo está RODANDO no cluster!' || echo '🔴 Algoritmo NÃO está sendo executado.'"

stop-mandelbrot: ## Para a execução do mandelbrot no cluster
	@echo "Parando a execução do mandelbrot no cluster e em todos os nós..."
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "killall -9 mpirun mandelbrot 2>/dev/null || true; if [ -f $(REMOTE_HOST_FILE) ]; then for node in \$$(sed 's/ .*//' $(REMOTE_HOST_FILE) | sort -u); do ssh \$$node 'killall -9 mandelbrot 2>/dev/null' < /dev/null || true; done; fi"

clean-notes-mandelbrot: ## Apaga os resultados do mandelbrot (local e VPS)
	@echo "Limpando análises do mandelbrot na VPS e localmente"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_MANDELBROT_NOTES_DIR)"
	rm -rf $(LOCAL_NOTES_DIR)/mandelbrot

### Mandelbrot SPMD (Ingênuo)

build-spmd: ## Compila o mandelbrot_spmd com mpicc
	@echo "Compilando mandelbrot_spmd com mpicc"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "cd $(REMOTE_SPMD_DIR) && mpicc -O2 main.c lib/complex.c lib/mandelbrot.c -o mandelbrot_spmd -lm"

run-spmd: ## Executa o mandelbrot_spmd em background no cluster
	@echo "Executando mandelbrot_spmd no cluster com nohup em background"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_SPMD_NOTES_DIR) && mkdir -p $(REMOTE_PICTURES_DIR)/mandelbrot_spmd && cd $(REMOTE_SPMD_DIR) && echo 'nohup mpirun -np $(NP) -machinefile $(REMOTE_HOST_FILE) ./mandelbrot_spmd $(PARS) $(REMOTE_PICTURES_DIR)/mandelbrot_spmd/spmd-$(RUN_ID).ppm > $(REMOTE_SPMD_NOTES_DIR)/spmd-$(RUN_ID).log 2>&1 < /dev/null &' > run_bg.sh && bash run_bg.sh"

check-spmd: ## Checa se o mandelbrot_spmd está rodando no cluster
	@echo "Verificando status do processo no cluster..."
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "pgrep -f '[m]pirun.*mandelbrot_spmd' > /dev/null && echo '🟢 Algoritmo SPMD está RODANDO no cluster!' || echo '🔴 Algoritmo SPMD NÃO está sendo executado.'"

clean-notes-spmd: ## Apaga os resultados do mandelbrot_spmd (local e VPS)
	@echo "Limpando análises do SPMD na VPS e localmente"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_SPMD_NOTES_DIR)"
	rm -rf $(LOCAL_NOTES_DIR)/mandelbrot_spmd

### Serial

build-serial: ## Compila o serial com gcc
	@echo "Compilando serial com gcc"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "cd $(REMOTE_SERIAL_DIR) && gcc -O2 image_generator.c complex.c mandelbrot.c -o serial_app -lm"

run-serial: ## Executa o serial em background no cluster
	@echo "Executando serial no cluster com nohup em background"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_SERIAL_NOTES_DIR) && mkdir -p $(REMOTE_SERIAL_PICTURES_DIR) && cd $(REMOTE_SERIAL_DIR) && echo 'nohup ./serial_app $(PARS) $(REMOTE_SERIAL_PICTURES_DIR)/serial-$(RUN_ID).ppm > $(REMOTE_SERIAL_NOTES_DIR)/serial-$(RUN_ID).log 2>&1 < /dev/null &' > run_bg.sh && bash run_bg.sh"

check-serial: ## Checa se o serial está rodando no cluster
	@echo "Verificando status do processo no cluster..."
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "pgrep -f './serial_app' > /dev/null && echo '🟢 Algoritmo serial está RODANDO no cluster!' || echo '🔴 Algoritmo serial NÃO está sendo executado.'"

clean-notes-serial: ## Apaga os resultados do serial (local e VPS)
	@echo "Limpando análises do serial na VPS e localmente"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_SERIAL_NOTES_DIR)"
	rm -rf $(LOCAL_NOTES_DIR)/serial