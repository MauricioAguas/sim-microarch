import os
import subprocess
import json
import time
import csv

# --- Rutas principales ---
GEM5 = "./build/ARM/gem5.fast"
CONFIG_SCRIPT = "scripts/CortexA76_scripts_gem5/CortexA76.py"
GEM5_TO_MCPAT = "McPAT/gem5toMcPAT_cortexA76.py"
MCPAT_EXEC = "./mcpat/mcpat"
MCPAT_TEMPLATE = "McPAT/ARM_A76_2.1GHz.xml"
OUTPUT_DIR = "greedy_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Archivo CSV para el historial ---
history_path = os.path.join(OUTPUT_DIR, "history.csv")
if not os.path.exists(history_path):
    with open(history_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Iteración", "Parámetro", "Valor probado",
            "EDP", "Energía", "CPI", "Leakage", "RuntimeDynamic",
            "¿Mejor configuración?", "Configuración completa"
        ])

# --- Configuración inicial ---
base_config = {
    "l1i_size": "64kB",
    "l1d_size": "64kB",
    "l2_size": "512kB",
    "fetch_width": 4,
    "commit_width": 4,
    "branch_predictor_type": 10
}

# --- Espacio de búsqueda limitado ---
parameter_space = {
    "l1i_size": ["32kB", "64kB", "128kB"],
    "l1d_size": ["32kB", "64kB", "128kB"],
    "l2_size": ["256kB", "512kB", "1MB"],
    "fetch_width": [2, 4, 6],
    "commit_width": [2, 4, 6],
    "branch_predictor_type": [7, 10]
}

# --- Función para correr simulación + análisis ---
def run_simulation(config, param_changed):
    name = "_".join([f"{k}{v}" for k, v in config.items()])
    outdir = os.path.join(OUTPUT_DIR, f"{param_changed}_{name}")
    os.makedirs(outdir, exist_ok=True)

    # Ejecutar gem5
    cmd = [
        GEM5,
        f"--outdir={outdir}",
        CONFIG_SCRIPT,
        "-c", "workloads/jpeg2k_dec/jpg2k_dec",
        "-o", "\"-i workloads/jpeg2k_dec/jpg2kdec_testfile.j2k -o image.pgm\"",
        f"--l1i_size={config['l1i_size']}",
        f"--l1d_size={config['l1d_size']}",
        f"--l2_size={config['l2_size']}",
        f"--fetch_width={config['fetch_width']}",
        f"--commit_width={config['commit_width']}",
        f"--branch_predictor_type={config['branch_predictor_type']}"
    ]
    subprocess.run(" ".join(cmd), shell=True, check=True)

    stats = os.path.join(outdir, "stats.txt")
    cfg = os.path.join(outdir, "config.json")
    xml = os.path.join(outdir, "config.xml")

    # Convertir a XML para McPAT
    subprocess.run(["python3", GEM5_TO_MCPAT, stats, cfg, MCPAT_TEMPLATE], check=True)
    if not os.path.exists(xml) and os.path.exists("config.xml"):
        os.rename("config.xml", xml)

    # Ejecutar McPAT
    mcpat_out = subprocess.run([MCPAT_EXEC, "-infile", xml, "-print_level", "1"], capture_output=True, text=True)
    output = mcpat_out.stdout
    with open(os.path.join(outdir, "power_report.txt"), "w") as f:
        f.write(output)

    # Extraer datos
    leakage = runtime = cpi = None
    for line in output.splitlines():
        if "Total Leakage" in line:
            leakage = float(line.split("=")[1].split()[0])
        if "Runtime Dynamic" in line:
            runtime = float(line.split("=")[1].split()[0])
    with open(stats) as f:
        for l in f:
            if "system.cpu.cpi" in l:
                cpi = float(l.split()[1])
                break

    if leakage and runtime and cpi:
        energy = (leakage + runtime) * cpi
        edp = energy * cpi
        return {"edp": edp, "energy": energy, "leakage": leakage, "runtime": runtime, "cpi": cpi}
    return None


# --- Algoritmo Greedy con registro histórico ---
current_config = base_config.copy()
best_result = run_simulation(current_config, "base")
iteration = 1

print(f"Configuración inicial EDP={best_result['edp']:.6f}\n")

improvement = True
while improvement:
    improvement = False
    for param, values in parameter_space.items():
        best_local = best_result
        for val in values:
            if val == current_config[param]:
                continue

            test_config = current_config.copy()
            test_config[param] = val
            print(f"[Iter {iteration}] Probando {param}={val}...")
            result = run_simulation(test_config, param)

            # Guardar en CSV cada intento
            with open(history_path, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    iteration,
                    param, val,
                    result["edp"] if result else "NaN",
                    result["energy"] if result else "NaN",
                    result["cpi"] if result else "NaN",
                    result["leakage"] if result else "NaN",
                    result["runtime"] if result else "NaN",
                    "YES" if result and result["edp"] < best_local["edp"] else "NO",
                    json.dumps(test_config)
                ])

            if result and result["edp"] < best_local["edp"]:
                print(f"  → Mejora: {best_local['edp']:.6f} → {result['edp']:.6f}")
                best_local = result
                current_config[param] = val
                improvement = True
            iteration += 1

        best_result = best_local

print("\nFinalizado Greedy Optimization.")
print(f"Mejor configuración encontrada:\n{json.dumps(current_config, indent=2)}")
print(f"EDP final: {best_result['edp']:.6f}")
print(f"Historial completo guardado en: {history_path}")
