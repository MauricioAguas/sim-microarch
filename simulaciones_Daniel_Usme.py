import os
import subprocess
from time import sleep
import itertools

# Ruta al ejecutable y script de configuración
GEM5 = "./build/ARM/gem5.fast"
CONFIG_SCRIPT = "scripts/CortexA76_scripts_gem5/CortexA76.py"

# Directorio de salida
OUTPUT_DIR = "Simulaciones_usme"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Definición de valores posibles para cada parámetro
# (Combinaciones de estos generarán 100 simulaciones)
L1I_SIZES = ["32kB", "64kB", "128kB"]
L1D_SIZES = ["32kB", "64kB", "128kB"]
L2_SIZES = ["256kB", "512kB", "1MB", "2MB"]
L1_LAT = [1, 2, 4]
L2_LAT = [6, 9, 12]
FETCH_WIDTH = [2, 4, 6, 8]
DECODE_WIDTH = [2, 4, 6, 8]
COMMIT_WIDTH = [2, 4, 6, 8]
ASSOC = [2, 4, 8]
ROB_ENTRIES = [64, 128, 192, 256]
BTB_ENTRIES = [1024, 2048, 4096, 8192]
BRANCH_PREDICTOR = [0, 1, 7, 10]  # BiMode, LTAGE, TAGE, Tournament

# Generar todas las combinaciones y cortar a 100
param_combinations = list(itertools.product(
    L1I_SIZES, L1D_SIZES, L2_SIZES,
    L1_LAT, L2_LAT,
    FETCH_WIDTH, DECODE_WIDTH, COMMIT_WIDTH,
    ASSOC, ROB_ENTRIES, BTB_ENTRIES, BRANCH_PREDICTOR
))[:100]

# Función de barra de progreso
def progress_bar(current, total, length=30):
    filled = int(length * current // total)
    bar = "█" * filled + "-" * (length - filled)
    print(f"\r[{bar}] {current}/{total} simulaciones", end="")

print(f"Iniciando {len(param_combinations)} simulaciones de exploración completa del Cortex-A76\n")

# Bucle principal de simulaciones
for i, params in enumerate(param_combinations, 1):
    (l1i, l1d, l2, l1_lat, l2_lat,
     fw, dw, cw, assoc, rob, btb, bp) = params

    outdir = os.path.join(
        OUTPUT_DIR,
        f"sim_{i:03d}_L1i{l1i}_L1d{l1d}_L2{l2}_FW{fw}_DW{dw}_CW{cw}_A{assoc}_ROB{rob}_BTB{btb}_BP{bp}"
    )
    os.makedirs(outdir, exist_ok=True)

    cmd = [
        GEM5,
        f"--outdir={outdir}",
        CONFIG_SCRIPT,
        "-c", "workloads/jpeg2k_dec/jpg2k_dec",
        "-o", "\"-i workloads/jpeg2k_dec/jpg2kdec_testfile.j2k -o image.pgm\"",
        f"--l1i_size={l1i}",
        f"--l1d_size={l1d}",
        f"--l2_size={l2}",
        f"--l1i_lat={l1_lat}",
        f"--l2_lat={l2_lat}",
        f"--l1i_assoc={assoc}",
        f"--l1d_assoc={assoc}",
        f"--l2_assoc={assoc}",
        f"--fetch_width={fw}",
        f"--decode_width={dw}",
        f"--commit_width={cw}",
        f"--rob_entries={rob}",
        f"--btb_entries={btb}",
        f"--branch_predictor_type={bp}"
    ]

    print(f"\nEjecutando simulación {i}/{len(param_combinations)}")
    print(f"L1i={l1i}, L1d={l1d}, L2={l2}, FW={fw}, DW={dw}, CW={cw}, Assoc={assoc}, ROB={rob}, BTB={btb}, BP={bp}")
    print(f"Salida: {outdir}")

    subprocess.run(" ".join(cmd), shell=True, check=True)

    progress_bar(i, len(param_combinations))
    sleep(1)

print("\n\nTodas las simulaciones finalizaron correctamente.")
print(f"Resultados guardados en: {os.path.abspath(OUTPUT_DIR)}")
