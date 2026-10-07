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

.PHONY: hello-cluster sync-cluster build-hello run-hello sync-notes clean-notes-hello all-hello build-mpi run-mpi all-mpi clean-notes-mpi

all-hello: sync-cluster build-hello run-hello

all-mpi: sync-cluster build-mpi run-mpi

hello-cluster:
	@echo "Conectando em $(USER)@$(HOST)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "cd $(REMOTE_HELLO_DIR) && ./main; exit"

build-hello:
	@echo "Compilando hello com -O2"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_HELLO_DIR) && cd $(REMOTE_HELLO_DIR) && gcc -O2 main.c -o main"

run-hello:
	@echo "Executando hello e salvando em $(REMOTE_HELLO_NOTES_DIR)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_HELLO_NOTES_DIR) && cd $(REMOTE_HELLO_DIR) && ( (time ./main > $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).out) 2> $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).time ) || ( rm -f $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).out $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).time && false )"

build-mpi:
	@echo "Compilando hello_mpi com mpicc"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_MPI_DIR) && cd $(REMOTE_MPI_DIR) && mpicc -O2 hello_mpi.c -o hello_mpi"

run-mpi:
	@echo "Executando hello_mpi no cluster com nohup em background"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_MPI_NOTES_DIR) && cd $(REMOTE_MPI_DIR) && nohup mpirun -np $(NP) -machinefile $(REMOTE_HOST_FILE) ./hello_mpi $(PARS) > $(REMOTE_MPI_NOTES_DIR)/mpi-$(RUN_ID).log 2>&1 &"

sync-cluster:
	@echo "Removendo e substituindo $(REMOTE_DIR) em $(USER)@$(HOST)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_DIR)"
	$(SCP_CMD) -r -P $(shell echo $(ARGS) | tr -d -c 0-9) $(LOCAL_DIR) $(USER)@$(HOST):$(REMOTE_DIR)
	$(SCP_CMD) -P $(shell echo $(ARGS) | tr -d -c 0-9) $(HOST_FILE) $(USER)@$(HOST):$(REMOTE_HOST_FILE)

sync-notes:
	@echo "Baixando $(REMOTE_NOTES_DIR) de $(USER)@$(HOST) para $(LOCAL_NOTES_DIR)"
	mkdir -p $(LOCAL_NOTES_DIR)
	$(SCP_CMD) -r -P $(shell echo $(ARGS) | tr -d -c 0-9) $(USER)@$(HOST):$(REMOTE_NOTES_DIR)/. $(LOCAL_NOTES_DIR)/

clean-notes-hello:
	@echo "Limpando análises do hello na VPS e localmente"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_HELLO_NOTES_DIR)"
	rm -rf $(LOCAL_NOTES_DIR)/hello

clean-notes-mpi:
	@echo "Limpando análises do mpi na VPS e localmente"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_MPI_NOTES_DIR)"
	rm -rf $(LOCAL_NOTES_DIR)/mpi