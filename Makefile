include config.mk

HOST ?= $(IP)
LOCAL_DIR := src/cluster
REMOTE_DIR := ~/cluster

LOCAL_HELLO_DIR := $(LOCAL_DIR)/hello
REMOTE_HELLO_DIR := $(REMOTE_DIR)/hello

LOCAL_NOTES_DIR := src/notes
REMOTE_NOTES_DIR := ~/notes
REMOTE_HELLO_NOTES_DIR := $(REMOTE_NOTES_DIR)/hello

RUN_ID := $(shell date +%Y%m%d-%H%M%S)

ifneq ($(PASSWORD),)
    SSH_CMD := sshpass -p '$(PASSWORD)' ssh
    SCP_CMD := sshpass -p '$(PASSWORD)' scp
else
    SSH_CMD := ssh
    SCP_CMD := scp
endif

.PHONY: hello-cluster sync-cluster build-hello run-hello sync-notes clean-notes-hello all-hello

all-hello: sync-cluster build-hello run-hello sync-notes

hello-cluster:
	@echo "Conectando em $(USER)@$(HOST)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "cd $(REMOTE_HELLO_DIR) && ./main; exit"

build-hello:
	@echo "Compilando hello com -O2"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_HELLO_DIR) && cd $(REMOTE_HELLO_DIR) && gcc -O2 main.c -o main"

run-hello:
	@echo "Executando hello e salvando em $(REMOTE_HELLO_NOTES_DIR)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "mkdir -p $(REMOTE_HELLO_NOTES_DIR) && cd $(REMOTE_HELLO_DIR) && ( (time ./main > $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).out) 2> $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).time ) || ( rm -f $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).out $(REMOTE_HELLO_NOTES_DIR)/hello-$(RUN_ID).time && false )"

sync-cluster:
	@echo "Removendo e substituindo $(REMOTE_DIR) em $(USER)@$(HOST)"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_DIR)"
	$(SCP_CMD) -r -P $(shell echo $(ARGS) | tr -d -c 0-9) $(LOCAL_DIR) $(USER)@$(HOST):$(REMOTE_DIR)

sync-notes:
	@echo "Baixando $(REMOTE_NOTES_DIR) de $(USER)@$(HOST) para $(LOCAL_NOTES_DIR)"
	mkdir -p $(LOCAL_NOTES_DIR)
	$(SCP_CMD) -r -P $(shell echo $(ARGS) | tr -d -c 0-9) $(USER)@$(HOST):$(REMOTE_NOTES_DIR)/. $(LOCAL_NOTES_DIR)/

clean-notes-hello:
	@echo "Limpando análises do hello na VPS e localmente"
	$(SSH_CMD) $(ARGS) $(USER)@$(HOST) "rm -rf $(REMOTE_HELLO_NOTES_DIR)"
	rm -rf $(LOCAL_NOTES_DIR)/hello