import csv
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# CONFIGURAÇÃO DO EXPERIMENTO
# ============================================================

RESOURCE_COUNTS = [
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

WARMUP = True
PAUSE_BETWEEN_ITERATIONS = 2

PROJECT_DIR = Path(__file__).resolve().parent

RESULTS_FILE = PROJECT_DIR / "results.csv"
SUMMARY_FILE = PROJECT_DIR / "summary.csv"


# ============================================================
# AMBIENTE
# ============================================================

env = os.environ.copy()

passphrase_file = PROJECT_DIR / ".pulumi-passphrase"

if (
    "PULUMI_CONFIG_PASSPHRASE" not in env
    and "PULUMI_CONFIG_PASSPHRASE_FILE" not in env
):
    if passphrase_file.exists():
        env["PULUMI_CONFIG_PASSPHRASE_FILE"] = str(passphrase_file)
    else:
        print("ERRO:")
        print("Nenhuma passphrase do Pulumi foi configurada.")
        print()
        print("Crie .pulumi-passphrase ou exporte:")
        print("PULUMI_CONFIG_PASSPHRASE")
        sys.exit(1)

# Evita consulta de atualização da CLI durante o benchmark.
env["PULUMI_SKIP_UPDATE_CHECK"] = "true"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def check_command(command):
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        return result.returncode == 0

    except FileNotFoundError:
        return False


def run_pulumi(command, resource_count, parallelism):
    command_env = env.copy()

    command_env["BENCHMARK_RESOURCE_COUNT"] = str(resource_count)

    pulumi_command = [
        "pulumi",
        command,
        "--yes",
        "--skip-preview",
        "--parallel",
        str(parallelism),
        "--suppress-progress",
        "--suppress-outputs",
        "--suppress-permalink",
        "--color",
        "never",
    ]

    start = time.perf_counter()

    result = subprocess.run(
        pulumi_command,
        cwd=PROJECT_DIR,
        env=command_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    end = time.perf_counter()

    elapsed = end - start

    return result.returncode == 0, elapsed, result.stderr


def cleanup(resource_count, parallelism):
    print("Garantindo que a stack esteja vazia...")

    success, _, error = run_pulumi(
        "destroy",
        resource_count,
        parallelism,
    )

    if not success:
        print("Falha durante cleanup inicial:")
        print(error)
        sys.exit(1)


def percentile(values, percentile_value):
    values = sorted(values)

    if not values:
        return 0

    rank = math.ceil(
        percentile_value / 100 * len(values)
    )

    rank = max(1, rank)

    return values[rank - 1]


# ============================================================
# VERIFICAÇÕES
# ============================================================

print()
print("============================================")
print("Pulumi Performance Benchmark")
print("============================================")
print()

print("Verificando Docker...")

if not check_command(["docker", "info"]):
    print("ERRO: Docker não está disponível.")
    print("Abra o Docker Desktop e tente novamente.")
    sys.exit(1)

print("Docker: OK")


print("Verificando Pulumi...")

if not check_command(["pulumi", "version"]):
    print("ERRO: Pulumi CLI não foi encontrado.")
    sys.exit(1)

print("Pulumi: OK")


# ============================================================
# RESULTADOS
# ============================================================

results = []


# ============================================================
# CLEANUP INICIAL
# ============================================================

cleanup(
    RESOURCE_COUNTS[0],
    PARALLELISM_LEVELS[0],
)


# ============================================================
# WARM-UP
# ============================================================

if WARMUP:

    print()
    print("============================================")
    print("Warm-up")
    print("============================================")

    warmup_resources = RESOURCE_COUNTS[0]
    warmup_parallel = PARALLELISM_LEVELS[0]

    print(
        f"resources={warmup_resources} "
        f"parallel={warmup_parallel}"
    )

    success, warmup_up, error = run_pulumi(
        "up",
        warmup_resources,
        warmup_parallel,
    )

    if not success:
        print("Warm-up UP falhou:")
        print(error)
        sys.exit(1)

    success, warmup_destroy, error = run_pulumi(
        "destroy",
        warmup_resources,
        warmup_parallel,
    )

    if not success:
        print("Warm-up DESTROY falhou:")
        print(error)
        sys.exit(1)

    print(
        f"Warm-up concluído "
        f"(up={warmup_up:.3f}s, "
        f"destroy={warmup_destroy:.3f}s)"
    )


# ============================================================
# BENCHMARK
# ============================================================

for resource_count in RESOURCE_COUNTS:

    for parallelism in PARALLELISM_LEVELS:

        print()
        print("============================================")
        print(
            f"Scenario: resources={resource_count}, "
            f"parallel={parallelism}"
        )
        print("============================================")

        for iteration in range(1, ITERATIONS + 1):

            print()
            print(
                f"Iteration {iteration}/{ITERATIONS}"
            )

            # ------------------------
            # PULUMI UP
            # ------------------------

            print("  pulumi up...", end="", flush=True)

            success_up, up_time, error = run_pulumi(
                "up",
                resource_count,
                parallelism,
            )

            if not success_up:
                print(" FAILED")
                print(error)

                # Tentativa de limpeza antes de interromper.
                run_pulumi(
                    "destroy",
                    resource_count,
                    parallelism,
                )

                sys.exit(1)

            print(f" {up_time:.3f}s")


            # ------------------------
            # PULUMI DESTROY
            # ------------------------

            print(
                "  pulumi destroy...",
                end="",
                flush=True,
            )

            success_destroy, destroy_time, error = run_pulumi(
                "destroy",
                resource_count,
                parallelism,
            )

            if not success_destroy:
                print(" FAILED")
                print(error)
                sys.exit(1)

            print(f" {destroy_time:.3f}s")


            # ------------------------
            # TOTAL
            # ------------------------

            total_time = up_time + destroy_time

            print(
                f"  total: {total_time:.3f}s"
            )


            # ------------------------
            # REGISTRAR
            # ------------------------

            result = {
                "timestamp_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "iteration": iteration,
                "resources": resource_count,
                "parallelism": parallelism,
                "up_seconds": up_time,
                "destroy_seconds": destroy_time,
                "total_seconds": total_time,
                "success": True,
            }

            results.append(result)


            # Salva continuamente para evitar perder
            # resultados caso o experimento seja interrompido.
            with open(
                RESULTS_FILE,
                "w",
                newline="",
            ) as csvfile:

                fieldnames = [
                    "timestamp_utc",
                    "iteration",
                    "resources",
                    "parallelism",
                    "up_seconds",
                    "destroy_seconds",
                    "total_seconds",
                    "success",
                ]

                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=fieldnames,
                )

                writer.writeheader()
                writer.writerows(results)


            if PAUSE_BETWEEN_ITERATIONS > 0:
                time.sleep(PAUSE_BETWEEN_ITERATIONS)


# ============================================================
# ANÁLISE ESTATÍSTICA
# ============================================================

summary_rows = []

for resource_count in RESOURCE_COUNTS:

    for parallelism in PARALLELISM_LEVELS:

        scenario = [
            r
            for r in results
            if (
                r["resources"] == resource_count
                and
                r["parallelism"] == parallelism
            )
        ]

        up_values = [
            r["up_seconds"]
            for r in scenario
        ]

        destroy_values = [
            r["destroy_seconds"]
            for r in scenario
        ]

        total_values = [
            r["total_seconds"]
            for r in scenario
        ]

        summary_rows.append(
            {
                "resources": resource_count,
                "parallelism": parallelism,

                "up_mean": statistics.mean(up_values),
                "up_median": statistics.median(up_values),
                "up_stddev": (
                    statistics.stdev(up_values)
                    if len(up_values) > 1
                    else 0
                ),
                "up_min": min(up_values),
                "up_max": max(up_values),
                "up_p95": percentile(
                    up_values,
                    95,
                ),

                "destroy_mean": statistics.mean(
                    destroy_values
                ),
                "destroy_median": statistics.median(
                    destroy_values
                ),
                "destroy_stddev": (
                    statistics.stdev(destroy_values)
                    if len(destroy_values) > 1
                    else 0
                ),
                "destroy_min": min(destroy_values),
                "destroy_max": max(destroy_values),
                "destroy_p95": percentile(
                    destroy_values,
                    95,
                ),

                "total_mean": statistics.mean(
                    total_values
                ),
                "total_median": statistics.median(
                    total_values
                ),
                "total_stddev": (
                    statistics.stdev(total_values)
                    if len(total_values) > 1
                    else 0
                ),
                "total_min": min(total_values),
                "total_max": max(total_values),
                "total_p95": percentile(
                    total_values,
                    95,
                ),
            }
        )


with open(
    SUMMARY_FILE,
    "w",
    newline="",
) as csvfile:

    fieldnames = list(
        summary_rows[0].keys()
    )

    writer = csv.DictWriter(
        csvfile,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(summary_rows)


# ============================================================
# RESULTADO FINAL
# ============================================================

print()
print("============================================")
print("Benchmark concluído")
print("============================================")
print()

print(f"Resultados brutos: {RESULTS_FILE}")
print(f"Resumo estatístico: {SUMMARY_FILE}")

print()

for row in summary_rows:

    print(
        f"resources={row['resources']} "
        f"parallel={row['parallelism']}"
    )

    print(
        f"  UP      mean={row['up_mean']:.3f}s "
        f"median={row['up_median']:.3f}s "
        f"std={row['up_stddev']:.3f}s "
        f"p95={row['up_p95']:.3f}s"
    )

    print(
        f"  DESTROY mean={row['destroy_mean']:.3f}s "
        f"median={row['destroy_median']:.3f}s "
        f"std={row['destroy_stddev']:.3f}s "
        f"p95={row['destroy_p95']:.3f}s"
    )

    print(
        f"  TOTAL   mean={row['total_mean']:.3f}s "
        f"median={row['total_median']:.3f}s "
        f"std={row['total_stddev']:.3f}s "
        f"p95={row['total_p95']:.3f}s"
    )

    print()