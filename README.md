# Mandelbrot Cluster

Trabalho de MPI com memória distribuída para cálculo do conjunto de Mandelbrot em cluster.

A ideia do projeto é centralizar os dados e as análises na pasta `src/notes`, mantendo a execução e a sincronização do cluster separadas da organização dos resultados.

---

## Pre-requisitos e Instalação

### Na Máquina Local (Cliente)
Para executar os comandos do `Makefile` e a sincronização automática, instale as seguintes ferramentas:

```bash
sudo apt update && sudo apt install make openssh-client sshpass -y
```

- **`make`**: Gerenciador de automação dos alvos do projeto.
- **`openssh-client`**: Fornece os comandos `ssh` e `scp`.
- **`sshpass`**: (Opcional) Permite autenticação automática sem digitar a senha manualmente a cada comando.

### No Servidor Remoto (VPS / Cluster)
No servidor remoto, certifique-se de ter os compiladores instalados:

```bash
sudo apt update && sudo apt install build-essential gcc -y
```

---

## Configuração Inicial

1. Crie o arquivo `config.mk` baseado no exemplo `config.example.mk`:

```bash
cp config.example.mk config.mk
```

2. Edite o `config.mk` com as credenciais do seu cluster:

```makefile
IP=lacad.uefs.br
HOST=lacad.uefs.br
USER=grupob
PASSWORD=sua_senha_aqui
ARGS=-p8107
```

---

## Como Executar

### Pipeline Completo Automático
Para sincronizar o código, compilar, executar e baixar os relatórios de análise para a máquina local com um único comando:

```bash
make all-hello
```

---

## Comandos Disponíveis (`Makefile`)

| Comando | Descrição |
| :--- | :--- |
| `make all-hello` | Executa todo o fluxo: `sync-cluster` ➔ `build-hello` ➔ `run-hello` ➔ `sync-notes` |
| `make sync-cluster` | Sincroniza a pasta local `src/cluster` para `~/cluster` na VPS |
| `make build-hello` | Compila o programa `hello` na VPS (`gcc -O2`) |
| `make run-hello` | Executa o programa `hello` na VPS e salva `.out` e `.time` em `~/notes/hello/` |
| `make sync-notes` | Baixa os resultados da VPS (`~/notes/`) para a pasta local (`src/notes/`) |
| `make clean-notes-hello` | Limpa os relatórios de análise do `hello` tanto na VPS quanto localmente |

---

## Arquivos e Estrutura

- `Makefile` — Regras de compilação, envio e análise do projeto.
- `config.mk` — Configurações locais de IP, usuário, porta e senha (ignorado pelo git).
- `config.example.mk` — Modelo de configuração para novos desenvolvedores.
- `src/cluster/` — Código fonte a ser sincronizado e executado no cluster.
- `src/notes/` — Pasta local onde ficam armazenadas as análises e medições de tempo.
