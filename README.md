# Teste de Performance do Pulumi

Projeto simples de benchmark para medir o desempenho do Pulumi durante o provisionamento e a destruição de infraestrutura utilizando containers Docker.

## Objetivo

O objetivo deste projeto é medir:

- Tempo de provisionamento da infraestrutura com `pulumi up`
- Tempo de destruição da infraestrutura com `pulumi destroy`
- Tempo total do ciclo
- Variação de desempenho de acordo com a quantidade de recursos
- Impacto do nível de paralelismo do Pulumi

## Requisitos

- Python 3
- Pulumi CLI
- Docker Desktop
- Provider Docker do Pulumi

## Configuração

Crie e ative um ambiente virtual Python:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Configure o Pulumi para utilizar armazenamento local:

```bash
pulumi login --local
```

Certifique-se de que o Docker Desktop esteja em execução:

```bash
docker info
```

Baixe previamente a imagem do Nginx:

```bash
docker pull nginx:alpine
```

Isso evita que o tempo de download da imagem interfira nos resultados do benchmark.

## Passphrase do Pulumi

O benchmark pode utilizar um arquivo local contendo a passphrase da stack do Pulumi.

Crie o arquivo:

```bash
printf '%s' 'SUA_SENHA_DO_PULUMI' > .pulumi-passphrase
chmod 600 .pulumi-passphrase
```

O arquivo `.pulumi-passphrase` não deve ser enviado para o Git.

Adicione-o ao `.gitignore`:

```text
.pulumi-passphrase
```

## Executando o benchmark

Ative o ambiente virtual:

```bash
source venv/bin/activate
```

Execute:

```bash
python benchmark.py
```

O benchmark realiza automaticamente o seguinte ciclo:

```text
pulumi up
    ↓
medição do tempo de provisionamento
    ↓
pulumi destroy
    ↓
medição do tempo de destruição
    ↓
repetição do experimento
```

Antes das medições, também é realizada uma execução de warm-up para reduzir possíveis interferências relacionadas à inicialização do ambiente.

## Configuração do experimento

Os principais parâmetros do experimento estão definidos no arquivo `benchmark.py`.

Exemplo:

```python
RESOURCE_COUNTS = [
    5,
    10,
    25,
    50,
    100,
]

PARALLELISM_LEVELS = [
    1,
    2,
    4,
    8,
    16,
]

ITERATIONS = 30
```

### `RESOURCE_COUNTS`

Define a quantidade de containers Docker que serão provisionados.

### `PARALLELISM_LEVELS`

Define a quantidade máxima de operações de recursos que o Pulumi pode executar simultaneamente.

### `ITERATIONS`

Define quantas vezes cada cenário será executado.

## Resultados

O benchmark gera dois arquivos principais.

### `results.csv`

Contém os resultados individuais de cada execução.

Exemplo:

```csv
timestamp_utc,iteration,resources,parallelism,up_seconds,destroy_seconds,total_seconds,success
2026-09-24T10:00:00+00:00,1,10,16,1.521,0.934,2.455,True
```

As principais métricas são:

- `up_seconds`: tempo de provisionamento
- `destroy_seconds`: tempo de destruição
- `total_seconds`: tempo total do ciclo
- `resources`: quantidade de recursos
- `parallelism`: nível de paralelismo
- `iteration`: número da repetição

### `summary.csv`

Contém as estatísticas agregadas de cada cenário, incluindo:

- Média
- Mediana
- Desvio padrão
- Mínimo
- Máximo
- Percentil 95 (P95)

## Estrutura do projeto

```text
pulumi-performance-test/
├── __main__.py
├── benchmark.py
├── Pulumi.yaml
├── Pulumi.dev.yaml
├── requirements.txt
├── results.csv
├── summary.csv
└── venv/
```

Arquivos locais como `.pulumi-passphrase` e `venv/` não devem ser enviados para o repositório.

## Observações

Os tempos obtidos representam a latência end-to-end de provisionamento e destruição da infraestrutura.

A medição inclui componentes como:

```text
Pulumi CLI
    +
Runtime Python
    +
Pulumi Engine
    +
Provider Docker
    +
Docker API
    +
Criação/remoção dos containers
```

Portanto, os resultados devem ser interpretados como o desempenho do processo de provisionamento de infraestrutura utilizando Pulumi, e não exclusivamente como o tempo interno de execução do Pulumi.