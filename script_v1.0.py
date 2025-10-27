import subprocess
import os
import re
import csv

EXE = "./build/ARM/gem5.fast"
SCRIPT = "scripts/scripts/CortexA76.py"
BIN = "workloads/jpeg2k_dec/jpg2k_dec"
OPTS = "'-i workloads/jpeg2k_dec/jpg2kdec_testfile.j2k -o image.pgm'"

# Espacio de diseño
L1I_SIZES = ["32kB", "64kB"]
L1D_SIZES = ["32kB", "64kB"]
L1D_ASSOCS = [4, 8]
ROB_ENTRIES = [128, 192]
ISSUE_WIDTHS = [6, 8]

def run_simulation(l1i, l1d, l1d_assoc, rob, issue_width):
    tag = f"L1I_{l1i}_L1D_{l1d}_L1DA_{l1d_assoc}_ROB_{rob}_IW_{issue_width}"
    print(f"Ejecutando simulación: {tag}")
    
    cmd = [
        EXE, SCRIPT,
        "-c", BIN,
        "-o", OPTS,
        f"--l1i_size={l1i}",
        f"--l1d_size={l1d}",
        f"--l1d_assoc={l1d_assoc}",
        f"--rob_entries={rob}",
        f"--issue_width={issue_width}"
    ]
    
    subprocess.run(" ".join(cmd), shell=True, check=True)
    
    os.rename("m5out/stats.txt", f"stats_{tag}.txt")
    os.rename("m5out/config.json", f"config_{tag}.json")
    
    return tag

def generar_xml_mcpat(tag, template_xml="scripts/McPAT/ARM_A76_2.1GHz.xml"):
    stats_file = f"stats_{tag}.txt"
    config_file = f"config_{tag}.json"
    xml_output = f"config_{tag}.xml"
    convert_script = "scripts/McPAT/gem5toMcPAT_cortexA76.py"
    
    cmd = ["python3", convert_script, stats_file, config_file, template_xml]
    with open(xml_output, "w") as outxml:
        subprocess.run(cmd, check=True, stdout=outxml, stderr=subprocess.PIPE)
    
    return xml_output

def ejecutar_mcpat(xml_file, tag, mcpat_exec="./mcpat/mcpat"):
    salida_mcpat = f"mcpat_{tag}.txt"
    cmd = [mcpat_exec, "-infile", xml_file, "-print_level", "1"]
    
    with open(salida_mcpat, "w") as fout:
        subprocess.run(cmd, check=True, stdout=fout)
    
    return salida_mcpat

def extraer_runtime_dynamic(mcpat_file):
    power = None
    with open(mcpat_file, "r") as f:
        inside_processor = False
        for line in f:
            if "Processor:" in line:
                inside_processor = True
            elif inside_processor and "Runtime Dynamic =" in line:
                parts = line.strip().split()
                power = float(parts[-2])
                break
    return power

def extraer_total_leakage(mcpat_file):
    leakage = None
    with open(mcpat_file, "r") as f:
        inside_processor = False
        for line in f:
            if "Processor:" in line:
                inside_processor = True
            elif inside_processor and "Total Leakage =" in line:
                parts = line.strip().split()
                leakage = float(parts[-2])
                break
    return leakage

def extraer_cpi(stats_file):
    cpi = None
    with open(stats_file, "r") as f:
        for line in f:
            if "system.cpu.cpi" in line and not line.strip().startswith("#"):
                cpi = float(line.split()[1])
                break
    return cpi

def main():
    results = []
    
    for l1i in L1I_SIZES:
        for l1d in L1D_SIZES:
            for l1d_assoc in L1D_ASSOCS:
                for rob in ROB_ENTRIES:
                    for issue_width in ISSUE_WIDTHS:
                        tag = run_simulation(l1i, l1d, l1d_assoc, rob, issue_width)
                        xml_file = generar_xml_mcpat(tag)
                        mcpat_file = ejecutar_mcpat(xml_file, tag)
                        
                        # Extraer métricas
                        cpi = extraer_cpi(f"stats_{tag}.txt")
                        runtime_dynamic = extraer_runtime_dynamic(mcpat_file)
                        total_leakage = extraer_total_leakage(mcpat_file)
                        
                        # Calcular Energy y EDP
                        energy = (total_leakage + runtime_dynamic) * cpi if (cpi and runtime_dynamic and total_leakage) else None
                        edp = energy * cpi if energy else None
                        
                        results.append({
                            "Tag": tag,
                            "L1I": l1i,
                            "L1D": l1d,
                            "L1D_Assoc": l1d_assoc,
                            "ROB": rob,
                            "Issue_Width": issue_width,
                            "CPI": cpi,
                            "Runtime_Dynamic_W": runtime_dynamic,
                            "Total_Leakage_W": total_leakage,
                            "Energy": energy,
                            "EDP": edp
                        })
    
    # Guardar resultados en CSV
    with open("dse_results.csv", "w", newline='') as csvfile:
        fieldnames = ["Tag", "L1I", "L1D", "L1D_Assoc", "ROB", "Issue_Width", 
                      "CPI", "Runtime_Dynamic_W", "Total_Leakage_W", "Energy", "EDP"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print("DSE completado. Resultados guardados en dse_results.csv")

if __name__ == "__main__":
    main()
