import subprocess
import os
import re
import csv
from itertools import product

# Configuración de rutas
EXE = "./build/ARM/gem5.fast"
SCRIPT = "scripts/scripts/CortexA76.py"
BIN_ENCODER = "workloads/jpeg2k_enc/jpg2k_enc"
BIN_DECODER = "workloads/jpeg2k_dec/jpg2k_dec"
OPTS_ENCODER = "'-i workloads/jpeg2k_enc/jpg2kenc_testfile.ppm -o compressed.j2k'"
OPTS_DECODER = "'-i workloads/jpeg2k_dec/jpg2kdec_testfile.j2k -o image.pgm'"

# DSE optimizado para JPEG2000 - Implementación por fases
# Fase 1: Cache Hierarchy (más crítico para JPEG2000)
L1D_SIZES_PHASE1 = ["32kB", "64kB", "128kB", "256kB"]
L1D_ASSOCS_PHASE1 = [4, 8, 16]
L2_SIZES_PHASE1 = ["256kB", "512kB", "1MB", "2MB"]  
L2_ASSOCS_PHASE1 = [8, 16, 24]

# Parámetros fijos para Fase 1
L1I_SIZE_FIXED = "64kB"
L1I_ASSOC_FIXED = 4
ROB_ENTRIES_FIXED = 128
ISSUE_WIDTH_FIXED = 4
DECODE_WIDTH_FIXED = 4
NUM_FU_INTALU_FIXED = 3
NUM_FU_FPSIMD_FIXED = 2

# Fase 2: Functional Units (después de cache optimization)
NUM_FU_INTALU_PHASE2 = [2, 3, 4, 6]
NUM_FU_FPSIMD_PHASE2 = [1, 2, 3, 4]
NUM_FU_READ_PHASE2 = [2, 3, 4]
NUM_FU_WRITE_PHASE2 = [1, 2, 3]

# Fase 3: Pipeline Parameters
ROB_ENTRIES_PHASE3 = [64, 128, 192]
ISSUE_WIDTH_PHASE3 = [2, 4, 6]
DECODE_WIDTH_PHASE3 = [2, 4, 6]

class DSEExplorer:
    def __init__(self, workload="both"):
        """
        workload: "encoder", "decoder", o "both"
        """
        self.workload = workload
        self.results = []
        self.phase_results = {"phase1": [], "phase2": [], "phase3": []}
        
    def get_workload_config(self, workload_type):
        """Retorna la configuración según el workload"""
        if workload_type == "encoder":
            return BIN_ENCODER, OPTS_ENCODER
        elif workload_type == "decoder":
            return BIN_DECODER, OPTS_DECODER
        else:
            raise ValueError("workload_type debe ser 'encoder' o 'decoder'")
    
    def run_simulation(self, params, workload_type, tag_suffix=""):
        """Ejecuta una simulación con los parámetros dados"""
        binary, opts = self.get_workload_config(workload_type)
        
        # Construir tag único
        tag_components = []
        for key, value in sorted(params.items()):
            tag_components.append(f"{key.upper()}_{value}")
        
        tag = f"{workload_type}_{'_'.join(tag_components)}{tag_suffix}"
        print(f"Ejecutando simulación: {tag}")
        
        # Construir comando gem5
        cmd = [
            EXE, SCRIPT,
            "-c", binary,
            "-o", opts
        ]
        
        # Agregar parámetros al comando
        for key, value in params.items():
            cmd.append(f"--{key}={value}")
        
        try:
            subprocess.run(" ".join(cmd), shell=True, check=True)
            
            # Renombrar archivos de salida
            os.rename("m5out/stats.txt", f"stats_{tag}.txt")
            os.rename("m5out/config.json", f"config_{tag}.json")
            
            return tag
            
        except subprocess.CalledProcessError as e:
            print(f"Error en simulación {tag}: {e}")
            return None

    def generar_xml_mcpat(self, tag, template_xml="scripts/McPAT/ARM_A76_2.1GHz.xml"):
        """Genera archivo XML para McPAT"""
        stats_file = f"stats_{tag}.txt"
        config_file = f"config_{tag}.json"
        xml_output = f"config_{tag}.xml"
        convert_script = "scripts/McPAT/gem5toMcPAT_cortexA76.py"
        
        cmd = ["python3", convert_script, stats_file, config_file, template_xml]
        
        try:
            with open(xml_output, "w") as outxml:
                subprocess.run(cmd, check=True, stdout=outxml, stderr=subprocess.PIPE)
            return xml_output
        except subprocess.CalledProcessError as e:
            print(f"Error generando XML McPAT para {tag}: {e}")
            return None

    def ejecutar_mcpat(self, xml_file, tag, mcpat_exec="./mcpat/mcpat"):
        """Ejecuta McPAT para análisis de potencia"""
        salida_mcpat = f"mcpat_{tag}.txt"
        cmd = [mcpat_exec, "-infile", xml_file, "-print_level", "1"]
        
        try:
            with open(salida_mcpat, "w") as fout:
                subprocess.run(cmd, check=True, stdout=fout)
            return salida_mcpat
        except subprocess.CalledProcessError as e:
            print(f"Error ejecutando McPAT para {tag}: {e}")
            return None

    def extraer_metricas(self, stats_file, mcpat_file):
        """Extrae métricas de performance y energía"""
        metrics = {}
        
        # CPI desde stats
        metrics['cpi'] = self.extraer_cpi(stats_file)
        
        # IPC calculado
        metrics['ipc'] = 1.0 / metrics['cpi'] if metrics['cpi'] else None
        
        # Cache miss rates específicos para JPEG2000
        metrics['l1d_miss_rate'] = self.extraer_cache_miss_rate(stats_file, "system.cpu.dcache.overall_miss_rate::total")
        metrics['l2_miss_rate'] = self.extraer_cache_miss_rate(stats_file, "system.l2.overall_miss_rate::total")
        
        # Utilización de unidades funcionales (importante para JPEG2000)
        metrics['intalu_utilization'] = self.extraer_fu_utilization(stats_file, "system.cpu.fuPool.IntALU")
        
        # Potencia desde McPAT
        if mcpat_file:
            metrics['runtime_dynamic'] = self.extraer_runtime_dynamic(mcpat_file)
            metrics['total_leakage'] = self.extraer_total_leakage(mcpat_file)
            
            # Calcular energía y EDP
            if metrics['cpi'] and metrics['runtime_dynamic'] and metrics['total_leakage']:
                metrics['energy'] = (metrics['total_leakage'] + metrics['runtime_dynamic']) * metrics['cpi']
                metrics['edp'] = metrics['energy'] * metrics['cpi']
        
        return metrics

    def extraer_cpi(self, stats_file):
        """Extrae CPI del archivo de estadísticas"""
        try:
            with open(stats_file, "r") as f:
                for line in f:
                    if "system.cpu.cpi" in line and not line.strip().startswith("#"):
                        return float(line.split()[1])
        except (FileNotFoundError, ValueError):
            pass
        return None

    def extraer_cache_miss_rate(self, stats_file, stat_name):
        """Extrae cache miss rate específico"""
        try:
            with open(stats_file, "r") as f:
                for line in f:
                    if stat_name in line and not line.strip().startswith("#"):
                        return float(line.split()[1])
        except (FileNotFoundError, ValueError):
            pass
        return None

    def extraer_fu_utilization(self, stats_file, fu_prefix):
        """Extrae utilización de unidades funcionales"""
        try:
            with open(stats_file, "r") as f:
                for line in f:
                    if f"{fu_prefix}_utilization" in line and not line.strip().startswith("#"):
                        return float(line.split()[1])
        except (FileNotFoundError, ValueError):
            pass
        return None

    def extraer_runtime_dynamic(self, mcpat_file):
        """Extrae potencia dinámica de McPAT"""
        try:
            with open(mcpat_file, "r") as f:
                inside_processor = False
                for line in f:
                    if "Processor:" in line:
                        inside_processor = True
                    elif inside_processor and "Runtime Dynamic =" in line:
                        parts = line.strip().split()
                        return float(parts[-2])
        except (FileNotFoundError, ValueError):
            pass
        return None

    def extraer_total_leakage(self, mcpat_file):
        """Extrae potencia de leakage de McPAT"""
        try:
            with open(mcpat_file, "r") as f:
                inside_processor = False
                for line in f:
                    if "Processor:" in line:
                        inside_processor = True
                    elif inside_processor and "Total Leakage =" in line:
                        parts = line.strip().split()
                        return float(parts[-2])
        except (FileNotFoundError, ValueError):
            pass
        return None

    def run_phase1_cache_exploration(self):
        """Fase 1: Exploración de jerarquía de cache"""
        print("=== FASE 1: Exploración de Cache Hierarchy ===")
        
        base_params = {
            "l1i_size": L1I_SIZE_FIXED,
            "l1i_assoc": L1I_ASSOC_FIXED,
            "rob_entries": ROB_ENTRIES_FIXED,
            "issue_width": ISSUE_WIDTH_FIXED,
            "decode_width": DECODE_WIDTH_FIXED
        }
        
        # Generar todas las combinaciones de cache
        cache_combinations = list(product(
            L1D_SIZES_PHASE1, L1D_ASSOCS_PHASE1,
            L2_SIZES_PHASE1, L2_ASSOCS_PHASE1
        ))
        
        print(f"Total configuraciones Fase 1: {len(cache_combinations)}")
        
        workloads = ["encoder", "decoder"] if self.workload == "both" else [self.workload]
        
        for workload_type in workloads:
            for l1d_size, l1d_assoc, l2_size, l2_assoc in cache_combinations:
                params = base_params.copy()
                params.update({
                    "l1d_size": l1d_size,
                    "l1d_assoc": l1d_assoc,
                    "l2_size": l2_size,
                    "l2_assoc": l2_assoc
                })
                
                tag = self.run_simulation(params, workload_type, "_phase1")
                if tag:
                    xml_file = self.generar_xml_mcpat(tag)
                    mcpat_file = self.ejecutar_mcpat(xml_file, tag) if xml_file else None
                    
                    metrics = self.extraer_metricas(f"stats_{tag}.txt", mcpat_file)
                    
                    result = {
                        "tag": tag,
                        "workload": workload_type,
                        "phase": 1,
                        **params,
                        **metrics
                    }
                    
                    self.phase_results["phase1"].append(result)
        
        # Guardar resultados de Fase 1
        self.save_phase_results("phase1")
        return self.find_best_cache_config()

    def find_best_cache_config(self):
        """Encuentra la mejor configuración de cache de la Fase 1"""
        if not self.phase_results["phase1"]:
            return None
            
        # Ordenar por EDP (Energy-Delay Product) - menor es mejor
        valid_results = [r for r in self.phase_results["phase1"] if r.get("edp") is not None]
        
        if not valid_results:
            print("No se encontraron resultados válidos en Fase 1")
            return None
            
        best_config = min(valid_results, key=lambda x: x["edp"])
        
        print(f"Mejor configuración de cache encontrada:")
        print(f"  L1D: {best_config['l1d_size']}, Assoc: {best_config['l1d_assoc']}")
        print(f"  L2: {best_config['l2_size']}, Assoc: {best_config['l2_assoc']}")
        print(f"  EDP: {best_config['edp']:.4f}")
        
        return {
            "l1d_size": best_config["l1d_size"],
            "l1d_assoc": best_config["l1d_assoc"], 
            "l2_size": best_config["l2_size"],
            "l2_assoc": best_config["l2_assoc"]
        }

    def save_phase_results(self, phase):
        """Guarda resultados de una fase en CSV"""
        if not self.phase_results[phase]:
            return
            
        filename = f"dse_jpeg2k_{phase}_results.csv"
        
        # Definir fieldnames basado en las claves del primer resultado
        sample_result = self.phase_results[phase][0]
        fieldnames = list(sample_result.keys())
        
        with open(filename, "w", newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.phase_results[phase])
            
        print(f"Resultados de {phase} guardados en {filename}")

    def run_full_exploration(self):
        """Ejecuta exploración completa en fases"""
        # Fase 1: Cache exploration
        best_cache_config = self.run_phase1_cache_exploration()
        
        if not best_cache_config:
            print("Error: No se pudo completar la Fase 1")
            return
            
        print("\\n=== Fase 1 completada. Iniciando análisis... ===")
        
        # Aquí podrías continuar con Fase 2 y 3 usando best_cache_config
        # Por ahora, solo implementamos Fase 1 para el DSE básico
        
        return best_cache_config

def main():
    """Función principal"""
    print("DSE para JPEG2000 Encoder/Decoder - Optimizado para características del workload")
    print("Basado en análisis comparativo vs MP3 workloads")
    
    # Crear explorador para ambos workloads
    explorer = DSEExplorer(workload="both")
    
    # Ejecutar exploración
    best_config = explorer.run_full_exploration()
    
    if best_config:
        print("\\nDSE completado exitosamente!")
        print(f"Mejor configuración encontrada: {best_config}")
    else:
        print("\\nError durante la exploración DSE")

if __name__ == "__main__":
    main()