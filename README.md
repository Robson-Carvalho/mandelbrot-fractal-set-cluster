# Mandelbrot Cluster

Trabalho de MPI com memória distribuída para cálculo do conjunto de Mandelbrot em cluster.

## Como executar

1. Ajuste os valores no arquivo `config.mk` com o usuário, host e porta do cluster.
2. No terminal, rode:

```bash
make hello-cluster
```

Esse comando executa a regra `hello-cluster`, que conecta ao host configurado e executa:

```bash
./hello_mpi
```

## Arquivos importantes

- `Makefile` — regras do projeto
- `config.mk` — configurações e variáveis de ambiente
- `config.example.mk` — exemplo de configuração

## Configuração

Antes de executar o comando, crie um arquivo `config.mk` com os dados do cluster. O arquivo `config.example.mk` serve como modelo para isso.
