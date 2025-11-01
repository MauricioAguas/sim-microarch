import subprocess
import os
import csv
from collections import defaultdict

# ==== CONFIGURACIÓN ====
EXE = "./build/ARM/gem5.fast"
SCRIPT = "scripts/scripts/CortexA76.py"

# ==== 6 WORKLOADS MULTIMEDIA (3 codecs × enc/dec) ====
WORKLOADS = {
    "jpeg2k_enc": {
        "bin": "workloads/jpeg2k_enc/jpg2k_enc",
        "opts": "'-i workloads/jpeg2k_enc/jpg2kenc_testfile.ppm -o compressed.j2k'"
    },
    "jpeg2k_dec": {
        "bin": "workloads/jpeg2k_dec/jpg2k_dec",
        "opts": "'-i workloads/jpeg2k_dec/jpg2kdec_testfile.j2k -o image.pgm'"
    },
    "mp3_enc": {
        "bin": "workloads/mp3_enc/mp3_enc",
        "opts": "'-i workloads/mp3_enc/sample.wav -o out.mp3'"
    },
    "mp3_dec": {
        "bin": "workloads/mp3_dec/mp3_dec",
        "opts": "'-i workloads/mp3_dec/sample.mp3 -o out.wav'"
    },
    "h264_enc": {
        "bin": "workloads/h264_enc/h264_enc",
        "opts": "'-i workloads/h264_enc/sample.yuv -o out.h264'"
    },
    "h264_dec": {
        "bin": "workloads/h264_dec/h264_dec",
        "opts": "'-i workloads/h264_dec/sample.h264 -o out.yuv'"
    }
}

# ==== CONFIGURACIONES PARA PROFILING ====
PROFILING_CONFIGS = {
    "small": {
        'l1d_size': '32kB',
        'l1i_size': '32kB', 
        'l2_size': '256kB',
        'rob_entries': 64,
        'issue_width': 2
    },
    "medium": {
        'l1d_size': '64kB',
        'l1i_size': '64kB', 
        'l2_size': '512kB',
        'rob_entries': 128,
        'issue_width': 4
    },
    "large": {
        'l1d_size': '128kB',
        'l1i_size': '128kB', 
        'l2_size': '1MB',
        'rob_entries': 192,
        'issue_width': 6
    }
}

class AccurateWorkloadProfiler:
    def __init__(self):
        self.profiling_results = []
        
    def run_gem5_simulation(self, workload_key, config_name, params):
        """Ejecuta una simulación gem5"""
        wl = WORKLOADS[workload_key]
        tag = f"profile_{workload_key}_{config_name}"
        
        print(f"[PROFILING] {workload_key} - {config_name}...")
        
        cmd = [
            EXE, SCRIPT,
            "-c", wl['bin'],
            "-o", wl['opts']
        ]
        
        for key, value in params.items():
            cmd.append(f"--{key}={value}")
        
        try:
            subprocess.run(" ".join(cmd), shell=True, check=True)
            os.rename("m5out/stats.txt", f"stats_{tag}.txt")
            os.rename("m5out/config.json", f"config_{tag}.json")
            print(f"[OK] {workload_key} - {config_name}")
            return tag
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] {workload_key} - {config_name}: {e}")
            return None
    
    def extract_accurate_metrics(self, stats_file):
        """Extrae métricas usando nombres exactos de gem5"""
        metrics = {
            # Performance básico
            'cpi': None,
            'ipc': None,
            'sim_seconds': None,
            
            # Instrucciones totales
            'total_committed_insts': None,
            'total_committed_ops': None,
            
            # Distribución de operaciones por COMMIT (más preciso)
            'committed_IntAlu': 0,
            'committed_IntMult': 0,
            'committed_IntDiv': 0,
            'committed_FloatTotal': 0,
            'committed_SimdTotal': 0,
            'committed_MemRead': 0,
            'committed_MemWrite': 0,
            'committed_Branches': 0,
            
            # Cache miss rates
            'l1d_miss_rate': None,
            'l1i_miss_rate': None,
            'l2_miss_rate': None,
            
            # Estadísticas de accesos
            'intAluAccesses': None,
            'fpAluAccesses': None,
            'vecAluAccesses': None
        }
        
        try:
            with open(stats_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    
                    # === PERFORMANCE BÁSICO ===
                    if 'system.cpu.cpi ' in line and not 'commitStats' in line:
                        metrics['cpi'] = float(line.split()[1])
                    elif 'system.cpu.ipc ' in line and not 'commitStats' in line:
                        metrics['ipc'] = float(line.split()[1])
                    elif 'simSeconds ' in line:
                        metrics['sim_seconds'] = float(line.split()[1])
                    
                    # === TOTAL DE INSTRUCCIONES ===
                    elif 'system.cpu.commitStats0.numInsts ' in line:
                        metrics['total_committed_insts'] = int(line.split()[1])
                    elif 'system.cpu.commitStats0.numOps ' in line:
                        metrics['total_committed_ops'] = int(line.split()[1])
                    
                    # === DISTRIBUCIÓN DE OPERACIONES (COMMITTED - más preciso) ===
                    elif 'system.cpu.commit.committedInstType0IntAlu ' in line:
                        metrics['committed_IntAlu'] = int(line.split()[1])
                    elif 'system.cpu.commit.committedInstType0IntMult ' in line:
                        metrics['committed_IntMult'] = int(line.split()[1])
                    elif 'system.cpu.commit.committedInstType0IntDiv ' in line:
                        metrics['committed_IntDiv'] = int(line.split()[1])
                    
                    # Float operations (sumar todos los tipos)
                    elif ('system.cpu.commit.committedInstType0Float' in line and 
                          not 'MemRead' in line and not 'MemWrite' in line):
                        metrics['committed_FloatTotal'] += int(line.split()[1])
                    
                    # SIMD operations (sumar todos los tipos)
                    elif 'system.cpu.commit.committedInstType0Simd' in line:
                        metrics['committed_SimdTotal'] += int(line.split()[1])
                    
                    # Memory operations
                    elif 'system.cpu.commit.committedInstType0MemRead ' in line:
                        metrics['committed_MemRead'] = int(line.split()[1])
                    elif 'system.cpu.commit.committedInstType0MemWrite ' in line:
                        metrics['committed_MemWrite'] = int(line.split()[1])
                    
                    # Branches
                    elif 'system.cpu.commit.branchMispredicts ' in line:
                        metrics['committed_Branches'] = int(line.split()[1])
                    
                    # === CACHE MISS RATES ===
                    elif 'system.cpu.dcache.overallMissRate::total ' in line:
                        metrics['l1d_miss_rate'] = float(line.split()[1])
                    elif 'system.cpu.icache.overallMissRate::total ' in line:
                        metrics['l1i_miss_rate'] = float(line.split()[1])
                    elif 'system.cpu.l2cache.overallMissRate::total ' in line:
                        metrics['l2_miss_rate'] = float(line.split()[1])
                    
                    # === ACCESOS A UNIDADES FUNCIONALES ===
                    elif 'system.cpu.intAluAccesses ' in line:
                        metrics['intAluAccesses'] = int(line.split()[1])
                    elif 'system.cpu.fpAluAccesses ' in line:
                        metrics['fpAluAccesses'] = int(line.split()[1])
                    elif 'system.cpu.vecAluAccesses ' in line:
                        metrics['vecAluAccesses'] = int(line.split()[1])
        
        except Exception as e:
            print(f"Error parsing {stats_file}: {e}")
        
        # Calcular porcentajes basados en instrucciones committed
        total_ops = metrics['total_committed_ops']
        if total_ops and total_ops > 0:
            metrics['integer_alu_pct'] = (metrics['committed_IntAlu'] / total_ops) * 100
            metrics['integer_mult_pct'] = (metrics['committed_IntMult'] / total_ops) * 100
            metrics['integer_div_pct'] = (metrics['committed_IntDiv'] / total_ops) * 100
            metrics['float_total_pct'] = (metrics['committed_FloatTotal'] / total_ops) * 100
            metrics['simd_total_pct'] = (metrics['committed_SimdTotal'] / total_ops) * 100
            metrics['mem_read_pct'] = (metrics['committed_MemRead'] / total_ops) * 100
            metrics['mem_write_pct'] = (metrics['committed_MemWrite'] / total_ops) * 100
            
            # Agrupar en categorías principales
            metrics['integer_total_pct'] = metrics['integer_alu_pct'] + metrics['integer_mult_pct'] + metrics['integer_div_pct']
            metrics['fp_simd_total_pct'] = metrics['float_total_pct'] + metrics['simd_total_pct']
            metrics['memory_total_pct'] = metrics['mem_read_pct'] + metrics['mem_write_pct']
        else:
            for key in ['integer_alu_pct', 'integer_mult_pct', 'integer_div_pct', 
                       'float_total_pct', 'simd_total_pct', 'mem_read_pct', 'mem_write_pct',
                       'integer_total_pct', 'fp_simd_total_pct', 'memory_total_pct']:
                metrics[key] = 0.0
        
        return metrics
    
    def run_profiling(self):
        """Ejecuta profiling completo"""
        print("=== PROFILING MULTIMEDIA CON PARSING CORRECTO ===")
        print(f"Total simulaciones: {len(WORKLOADS)} × {len(PROFILING_CONFIGS)} = {len(WORKLOADS) * len(PROFILING_CONFIGS)}")
        print()
        
        # Verificar workloads disponibles
        available_workloads = {}
        for wl_key, wl_info in WORKLOADS.items():
            if os.path.exists(wl_info['bin']):
                available_workloads[wl_key] = wl_info
            else:
                print(f"WARNING: {wl_key} no encontrado: {wl_info['bin']}")
        
        if not available_workloads:
            print("ERROR: No se encontraron workloads válidos")
            return
        
        print(f"Workloads disponibles: {list(available_workloads.keys())}")
        print()
        
        # Ejecutar simulaciones
        completed = 0
        total = len(available_workloads) * len(PROFILING_CONFIGS)
        
        for wl_key in available_workloads.keys():
            for config_name, config_params in PROFILING_CONFIGS.items():
                tag = self.run_gem5_simulation(wl_key, config_name, config_params)
                completed += 1
                
                if tag:
                    stats_file = f"stats_{tag}.txt"
                    metrics = self.extract_accurate_metrics(stats_file)
                    
                    result = {
                        'workload': wl_key,
                        'codec': wl_key.split('_')[0],
                        'type': wl_key.split('_')[1],
                        'config': config_name,
                        'tag': tag,
                        **config_params,
                        **metrics
                    }
                    
                    self.profiling_results.append(result)
                    
                    # Mostrar progreso con datos correctos
                    print(f"[{completed}/{total}] {wl_key} - {config_name}:")
                    print(f"  CPI: {metrics.get('cpi', 'N/A')}")
                    print(f"  IPC: {metrics.get('ipc', 'N/A')}")
                    print(f"  Integer Total: {metrics.get('integer_total_pct', 0):.1f}%")
                    print(f"  Integer ALU: {metrics.get('integer_alu_pct', 0):.1f}%")
                    print(f"  FP+SIMD: {metrics.get('fp_simd_total_pct', 0):.1f}%")
                    print(f"  Memory Total: {metrics.get('memory_total_pct', 0):.1f}%")
                    print(f"  L1D Miss Rate: {metrics.get('l1d_miss_rate', 'N/A')}")
                    print(f"  L1I Miss Rate: {metrics.get('l1i_miss_rate', 'N/A')}")
                    print()
        
        # Guardar y analizar
        self.save_results()
        recommended = self.analyze_results()
        
        return recommended
    
    def save_results(self):
        """Guarda resultados en CSV"""
        if not self.profiling_results:
            return
        
        filename = "profiling_multimedia_accurate.csv"
        fieldnames = list(self.profiling_results[0].keys())
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.profiling_results)
        
        print(f"[CSV] Guardado: {filename}")
    
    def analyze_results(self):
        """Análisis preciso basado en datos reales"""
        print("\\n=== ANÁLISIS PRECISO DE WORKLOADS ===")
        
        by_codec = defaultdict(list)
        for r in self.profiling_results:
            by_codec[r['codec']].append(r)
        
        recommendations = []
        
        for codec in ['jpeg2k', 'mp3', 'h264']:
            if codec not in by_codec:
                continue
            
            results = by_codec[codec]
            
            # Calcular promedios válidos
            valid_ipcs = [r['ipc'] for r in results if r['ipc'] is not None]
            valid_cpis = [r['cpi'] for r in results if r['cpi'] is not None]
            integer_pcts = [r['integer_total_pct'] for r in results]
            fp_simd_pcts = [r['fp_simd_total_pct'] for r in results]
            memory_pcts = [r['memory_total_pct'] for r in results]
            l1d_misses = [r['l1d_miss_rate'] for r in results if r['l1d_miss_rate'] is not None]
            
            # Estadísticas
            avg_ipc = sum(valid_ipcs) / len(valid_ipcs) if valid_ipcs else 0
            avg_cpi = sum(valid_cpis) / len(valid_cpis) if valid_cpis else 0
            avg_integer = sum(integer_pcts) / len(integer_pcts) if integer_pcts else 0
            avg_fp_simd = sum(fp_simd_pcts) / len(fp_simd_pcts) if fp_simd_pcts else 0
            avg_memory = sum(memory_pcts) / len(memory_pcts) if memory_pcts else 0
            avg_l1d_miss = sum(l1d_misses) / len(l1d_misses) if l1d_misses else 0
            
            # Sensibilidad (variabilidad entre configuraciones)
            ipc_range = (max(valid_ipcs) - min(valid_ipcs)) if len(valid_ipcs) > 1 else 0
            
            print(f"\\n{codec.upper()}:")
            print(f"  IPC: {avg_ipc:.3f} (rango: {ipc_range:.3f})")
            print(f"  CPI: {avg_cpi:.3f}")
            print(f"  Integer Total: {avg_integer:.1f}%")
            print(f"  FP+SIMD Total: {avg_fp_simd:.1f}%")
            print(f"  Memory Total: {avg_memory:.1f}%")
            print(f"  L1D Miss Rate: {avg_l1d_miss:.4f}")
            
            # Scoring basado en características reales
            dse_score = 0
            reasons = []
            
            # Integer dominance (como JPEG2000 en paper de compañeros)
            if avg_integer > 60:
                dse_score += 4
                reasons.append(f"Muy alto uso Integer ({avg_integer:.1f}% - similar a JPEG2000)")
            elif avg_integer > 40:
                dse_score += 3
                reasons.append(f"Alto uso Integer ({avg_integer:.1f}%)")
            elif avg_integer > 25:
                dse_score += 2
                reasons.append(f"Uso significativo Integer ({avg_integer:.1f}%)")
            
            # Memory bound (como MP3 en paper de compañeros)
            if avg_memory > 35:
                dse_score += 3
                reasons.append(f"Memory-bound ({avg_memory:.1f}% - similar a MP3)")
            elif avg_memory > 20:
                dse_score += 2
                reasons.append(f"Memory-intensive ({avg_memory:.1f}%)")
            
            # FP/SIMD (como H264 en paper de compañeros)
            if avg_fp_simd > 25:
                dse_score += 3
                reasons.append(f"Alto FP/SIMD ({avg_fp_simd:.1f}% - similar a H264)")
            elif avg_fp_simd > 15:
                dse_score += 2
                reasons.append(f"Uso significativo FP/SIMD ({avg_fp_simd:.1f}%)")
            elif avg_fp_simd > 5:
                dse_score += 1
                reasons.append(f"Algo de FP/SIMD ({avg_fp_simd:.1f}%)")
            
            # Cache sensitivity
            if avg_l1d_miss > 0.5:  # 50% miss rate
                dse_score += 3
                reasons.append(f"Muy alta L1D miss rate ({avg_l1d_miss:.3f})")
            elif avg_l1d_miss > 0.2:  # 20% miss rate
                dse_score += 2
                reasons.append(f"Alta L1D miss rate ({avg_l1d_miss:.3f})")
            elif avg_l1d_miss > 0.05:  # 5% miss rate
                dse_score += 1
                reasons.append(f"L1D miss rate notable ({avg_l1d_miss:.3f})")
            
            # Sensibilidad a configuración
            if ipc_range > 0.5:
                dse_score += 3
                reasons.append(f"Muy alta sensibilidad (IPC rango: {ipc_range:.3f})")
            elif ipc_range > 0.2:
                dse_score += 2
                reasons.append(f"Alta sensibilidad (IPC rango: {ipc_range:.3f})")
            elif ipc_range > 0.1:
                dse_score += 1
                reasons.append(f"Sensibilidad moderada (IPC rango: {ipc_range:.3f})")
            
            # Balance (múltiples oportunidades de optimización)
            categories_above_15 = sum([
                1 if avg_integer > 15 else 0,
                1 if avg_fp_simd > 15 else 0, 
                1 if avg_memory > 15 else 0
            ])
            
            if categories_above_15 >= 2:
                dse_score += 1
                reasons.append("Características balanceadas (múltiples vectores optimización)")
            
            recommendations.append({
                'codec': codec,
                'score': dse_score,
                'reasons': reasons,
                'avg_ipc': avg_ipc,
                'avg_cpi': avg_cpi,
                'sensitivity': ipc_range,
                'integer_pct': avg_integer,
                'fp_simd_pct': avg_fp_simd,
                'memory_pct': avg_memory,
                'l1d_miss': avg_l1d_miss
            })
        
        # Ordenar por score DSE
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        print("\\n=== RANKING PARA DSE AMPLIO ===")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\\n{i}. {rec['codec'].upper()} (Score DSE: {rec['score']})")
            print(f"   IPC promedio: {rec['avg_ipc']:.3f}")
            print(f"   CPI promedio: {rec['avg_cpi']:.3f}")
            print(f"   Sensibilidad: {rec['sensitivity']:.3f}")
            print(f"   Integer: {rec['integer_pct']:.1f}%")
            print(f"   FP+SIMD: {rec['fp_simd_pct']:.1f}%")
            print(f"   Memory: {rec['memory_pct']:.1f}%")
            print(f"   L1D Miss: {rec['l1d_miss']:.4f}")
            print("   Razones para DSE:")
            for reason in rec['reasons']:
                print(f"     • {reason}")
            
            if i == 1:
                print("   *** ALTAMENTE RECOMENDADO PARA DSE ***")
            elif i == 2:
                print("   *** SEGUNDA OPCIÓN ***")
        
        # Conclusión final
        if recommendations:
            best = recommendations[0]
            print(f"\\n=== CONCLUSIÓN FINAL ===")
            print(f"Workload ÓPTIMO para DSE amplio: {best['codec'].upper()}")
            print(f"Score DSE: {best['score']}")
            print(f"IPC promedio: {best['avg_ipc']:.3f}")
            print(f"Características dominantes:")
            print(f"  - Integer: {best['integer_pct']:.1f}%")
            print(f"  - FP+SIMD: {best['fp_simd_pct']:.1f}%")
            print(f"  - Memory: {best['memory_pct']:.1f}%")
            
            return best['codec']
        
        return None

def main():
    print("PROFILING MULTIMEDIA ")
    print("======================================\\n")
    
    profiler = AccurateWorkloadProfiler()
    recommended = profiler.run_profiling()
    
    print("\\n=== PROFILING COMPLETADO ===")
    print("Archivos generados:")
    print("  - profiling_multimedia_accurate.csv")
    print("  - stats_profile_*.txt")
    

if __name__ == "__main__":
    main()