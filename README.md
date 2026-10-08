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

- **Programa Hello (Sequencial):**
  ```bash
  make all-hello
  ```

- **Programa Mandelbrot (MPI Avançado):**
  ```bash
  make all-mandelbrot check-mandelbrot NP=4 PARS="2000 2000"
  ```
  *(O processo rodará em background, de forma desacoplada da sua máquina).*

---

## Fluxo de Execução do Mandelbrot

Como o cálculo do Mandelbrot pode ser demorado (especialmente para matrizes muito grandes), o fluxo de execução foi desenhado para não "travar" o seu terminal (execução assíncrona):

1. **Submissão Desacoplada (`run-mandelbrot`)**:
   O `Makefile` acessa a VPS via SSH e cria um script temporário chamado `run_bg.sh`. Esse script contém o comando `mpirun` com a flag `nohup` e `&`. O `Makefile` executa esse script e encerra imediatamente. Com isso, o cálculo fica executando lá no servidor em segundo plano, e a sua conexão SSH é liberada instantaneamente.
   
2. **Parâmetros Dinâmicos (`NP` e `PARS`)**:
   - `NP` (Number of Processes): É a quantidade total de Ranks que você deseja criar. O MPI se encarregará de distribuir essa quantidade de Ranks entre as máquinas listadas no `host_nodes`. Exemplo: `NP=8`.
   - `PARS`: Permite passar argumentos extras via linha de comando direto para o programa em C (chegando como `argv`). Isso evita ter que editar e recompilar o código a cada teste. Exemplo: `PARS="2000 2000"` (enviando as dimensões de `rows` e `columns`).

3. **Verificação de Status (`check-mandelbrot`)**:
   Enquanto o servidor está realizando as contas lá no background, você pode acompanhar se ele ainda está rodando com o comando:
   ```bash
   make check-mandelbrot
   ```
   Ele usa um `pgrep -f` inteligente para detectar o processo e retorna uma 🟢 **Bolinha Verde** se o algoritmo estiver vivo, ou 🔴 **Bolinha Vermelha** caso tenha finalizado.

4. **Sincronização dos Resultados (`sync-notes`)**:
   Quando a checagem der vermelho, significa que o algoritmo terminou o trabalho. Aí sim você deve baixar o arquivo de Log (`.log`) pesadão para sua máquina local:
   ```bash
   make sync-notes
   ```

---

## Comandos Disponíveis (`Makefile`)

| Comando | Descrição |
| :--- | :--- |
| `make all-hello` | Executa todo o fluxo do hello: `sync-cluster` ➔ `build-hello` ➔ `run-hello` ➔ `sync-notes` |
| `make all-mpi` | Executa todo o fluxo MPI: `sync-cluster` ➔ `build-mpi` ➔ `run-mpi` |
| `make all-mandelbrot` | Executa todo o fluxo Mandelbrot: `sync-cluster` ➔ `build-mandelbrot` ➔ `run-mandelbrot` |
| `make check-mandelbrot` | Verifica se o algoritmo Mandelbrot ainda está em execução na VPS (🟢/🔴) |
| `make sync-cluster` | Sincroniza a pasta local `src/cluster` e `host_nodes` para `~/cluster` no host remoto |
| `make build-hello` | Compila o programa `hello` no host remoto (`gcc -O2`) |
| `make run-hello` | Executa o programa `hello` no host remoto |
| `make build-mpi` | Compila o programa MPI no host remoto (`mpicc -O2 hello_mpi.c -o hello_mpi`) |
| `make run-mpi` | Executa o programa MPI via `mpirun` com `nohup` em background (`&`) |
| `make sync-notes` | Baixa os resultados do host remoto (`~/notes/`) para a pasta local (`src/notes/`) |
| `make clean-notes-hello` | Limpa os relatórios de análise do `hello` tanto no host quanto localmente |
| `make clean-notes-mpi` | Limpa os relatórios de análise do `mpi` tanto no host quanto localmente |
| `make clean-notes-mandelbrot` | Limpa os relatórios e logs do `mandelbrot` na VPS e localmente |

---

## Arquivos e Estrutura

- `Makefile` — Regras de compilação, envio e análise do projeto.
- `config.mk` — Configurações locais de IP/HOST, usuário, porta e senha (ignorado pelo git).
- `config.example.mk` — Modelo de configuração para novos desenvolvedores.
- `host_nodes` — Lista de nós de cômputo e slots para o `mpirun`.
- `src/cluster/` — Código fonte a ser sincronizado e executado no cluster.
- `src/notes/` — Pasta local onde ficam armazenadas as análises e medições de tempo.

