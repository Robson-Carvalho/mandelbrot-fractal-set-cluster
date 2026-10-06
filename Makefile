include config.mk

HOST ?= $(IP)

.PHONY: hello-cluster
hello-cluster:
	@echo "Conectando em $(USER)@$(HOST)"
	ssh $(ARGS) $(USER)@$(HOST) "./hello_mpi; exit"