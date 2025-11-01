import os
import csv
import glob
import re
from collections import defaultdict

class MultimediaProfilingAnalysis:
    def __init__(self):
        self.profiling_results = []
        
    def parse_tag_info(self, stats_filename):
        base_name = stats_filename.replace('stats_profile_', '').replace('.txt', '')
        parts = base_name.split('_')
        if len(parts) >= 3:
            return {
                'workload': f"{parts[0]}_{parts[1]}",
                'codec': parts[0],
                'type': parts[1],
                'config': parts[2],
                'tag': base_name
            }
        return None
    
    def extract_metrics(self, stats_file):
        metrics = {
            'cpi': None, 'ipc': None, 'sim_seconds': None,
            'No_OpClass': 0, 'IntAlu': 0, 'IntMult': 0, 'IntDiv': 0,
            'FloatAdd': 0, 'FloatCmp': 0, 'FloatCvt': 0, 'FloatMult': 0, 
            'FloatDiv': 0, 'FloatMisc': 0, 'FloatSqrt': 0,
            'SimdAdd': 0, 'SimdAlu': 0, 'SimdCmp': 0, 'SimdMisc': 0, 
            'SimdMult': 0, 'SimdMultAcc': 0, 'SimdSqrt': 0,
            'SimdFloatAdd': 0, 'SimdFloatAlu': 0, 'SimdFloatCmp': 0, 
            'SimdFloatCvt': 0, 'SimdFloatDiv': 0, 'SimdFloatMisc': 0,
            'SimdFloatMult': 0, 'SimdFloatMultAcc': 0, 'SimdFloatSqrt': 0,
            'MemRead': 0, 'MemWrite': 0,
            'l1d_miss_rate': None, 'l1i_miss_rate': None, 'l2_miss_rate': None
        }
        
        try:
            with open(stats_file, 'r') as f:
                data = f.read()
            
            # Extract performance metrics
            cpi_match = re.search(r'system\.cpu\.cpi\s+([\d.]+)', data)
            if cpi_match:
                metrics['cpi'] = float(cpi_match.group(1))
                metrics['ipc'] = 1.0 / metrics['cpi']
            
            sim_seconds_match = re.search(r'simSeconds\s+([\d.]+)', data)
            if sim_seconds_match:
                metrics['sim_seconds'] = float(sim_seconds_match.group(1))
            
            # Extract instruction type distribution
            stat_issued_pattern = r'system\.cpu\.statIssuedInstType_0::([a-zA-Z]+)\s+(\d+)\s+'
            stat_issued_matches = re.findall(stat_issued_pattern, data)
            
            for op_type, count in stat_issued_matches:
                if op_type in metrics:
                    metrics[op_type] = int(count)
            
            # Extract cache miss rates
            l1d_miss_match = re.search(r'system\.cpu\.dcache\.overallMissRate::total\s+([\d.]+)', data)
            if l1d_miss_match:
                metrics['l1d_miss_rate'] = float(l1d_miss_match.group(1))
            
            l1i_miss_match = re.search(r'system\.cpu\.icache\.overallMissRate::total\s+([\d.]+)', data)
            if l1i_miss_match:
                metrics['l1i_miss_rate'] = float(l1i_miss_match.group(1))
            
            l2_miss_match = re.search(r'system\.l2cache\.overallMissRate::total\s+([\d.]+)', data)
            if l2_miss_match:
                metrics['l2_miss_rate'] = float(l2_miss_match.group(1))
                
        except Exception as e:
            print(f"Error parsing {stats_file}: {e}")
        
        # Calculate percentages and group operations
        operation_keys = [k for k in metrics.keys() if k not in 
                         ['cpi', 'ipc', 'sim_seconds', 'l1d_miss_rate', 'l1i_miss_rate', 'l2_miss_rate']
                         and isinstance(metrics[k], int)]
        
        total_ops = sum([metrics[k] for k in operation_keys])
        
        if total_ops > 0:
            percentage_metrics = {}
            for key in operation_keys:
                percentage_metrics[f"{key}_pct"] = (metrics[key] / total_ops) * 100
            
            metrics.update(percentage_metrics)
            
            # Group operation categories
            metrics['Integer_total_pct'] = (
                metrics.get('IntAlu_pct', 0) + 
                metrics.get('IntMult_pct', 0) + 
                metrics.get('IntDiv_pct', 0)
            )
            
            metrics['Float_total_pct'] = (
                metrics.get('FloatAdd_pct', 0) + metrics.get('FloatCmp_pct', 0) +
                metrics.get('FloatCvt_pct', 0) + metrics.get('FloatMult_pct', 0) +
                metrics.get('FloatDiv_pct', 0) + metrics.get('FloatMisc_pct', 0) +
                metrics.get('FloatSqrt_pct', 0)
            )
            
            metrics['Simd_total_pct'] = (
                metrics.get('SimdAdd_pct', 0) + metrics.get('SimdAlu_pct', 0) +
                metrics.get('SimdCmp_pct', 0) + metrics.get('SimdMisc_pct', 0) +
                metrics.get('SimdMult_pct', 0) + metrics.get('SimdMultAcc_pct', 0) +
                metrics.get('SimdSqrt_pct', 0) + 
                metrics.get('SimdFloatAdd_pct', 0) + metrics.get('SimdFloatAlu_pct', 0) +
                metrics.get('SimdFloatCmp_pct', 0) + metrics.get('SimdFloatCvt_pct', 0) +
                metrics.get('SimdFloatDiv_pct', 0) + metrics.get('SimdFloatMisc_pct', 0) +
                metrics.get('SimdFloatMult_pct', 0) + metrics.get('SimdFloatMultAcc_pct', 0) +
                metrics.get('SimdFloatSqrt_pct', 0)
            )
            
            metrics['Memory_total_pct'] = (
                metrics.get('MemRead_pct', 0) + 
                metrics.get('MemWrite_pct', 0)
            )
            
            metrics['FP_SIMD_combined_pct'] = metrics['Float_total_pct'] + metrics['Simd_total_pct']
            
        else:
            for key in ['Integer_total_pct', 'Float_total_pct', 'Simd_total_pct', 
                       'Memory_total_pct', 'FP_SIMD_combined_pct']:
                metrics[key] = 0.0
        
        metrics['total_operations'] = total_ops
        return metrics
    
    def process_stats_files(self):
        """Process all stats files and extract metrics"""
        stats_files = glob.glob('stats_profile_*.txt')
        
        if not stats_files:
            print("No stats files found")
            return
        
        print(f"Processing {len(stats_files)} stats files...")
        
        for stats_file in sorted(stats_files):
            tag_info = self.parse_tag_info(stats_file)
            if not tag_info:
                continue
            
            print(f"Processing: {tag_info['workload']} - {tag_info['config']}")
            
            metrics = self.extract_metrics(stats_file)
            result = {**tag_info, **metrics}
            self.profiling_results.append(result)
        
        self.save_results()
        self.print_detailed_analysis()
    
    def save_results(self):
        """Save results to CSV"""
        filename = "profiling_results.csv"
        fieldnames = list(self.profiling_results[0].keys())
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.profiling_results)
        
        print(f"\\nResults saved to {filename}")
    
    def print_detailed_analysis(self):
        """Print comprehensive analysis"""
        by_codec = defaultdict(list)
        for r in self.profiling_results:
            by_codec[r['codec']].append(r)
        
        print("\\n" + "="*60)
        print("MULTIMEDIA WORKLOAD PROFILING ANALYSIS")
        print("="*60)
        
        for codec in ['jpeg2k', 'mp3', 'h264']:
            if codec in by_codec:
                results = by_codec[codec]
                
                print(f"\\n{codec.upper()} ({len(results)} configurations)")
                print("-" * 40)
                
                # Calculate averages
                valid_ipcs = [r['ipc'] for r in results if r['ipc'] is not None]
                integer_pcts = [r['Integer_total_pct'] for r in results]
                fp_simd_pcts = [r['FP_SIMD_combined_pct'] for r in results]
                memory_pcts = [r['Memory_total_pct'] for r in results]
                l1d_misses = [r['l1d_miss_rate'] for r in results if r['l1d_miss_rate'] is not None]
                
                avg_ipc = sum(valid_ipcs) / len(valid_ipcs) if valid_ipcs else 0
                avg_integer = sum(integer_pcts) / len(integer_pcts) if integer_pcts else 0
                avg_fp_simd = sum(fp_simd_pcts) / len(fp_simd_pcts) if fp_simd_pcts else 0
                avg_memory = sum(memory_pcts) / len(memory_pcts) if memory_pcts else 0
                avg_l1d_miss = sum(l1d_misses) / len(l1d_misses) if l1d_misses else 0
                
                # Print metrics
                print(f"Performance:")
                print(f"  Average IPC: {avg_ipc:.3f}")
                print(f"  IPC Range: {min(valid_ipcs):.3f} - {max(valid_ipcs):.3f}")
                
                print(f"\\nOperation Distribution:")
                print(f"  Integer Operations: {avg_integer:.1f}%")
                print(f"  FP+SIMD Operations: {avg_fp_simd:.1f}%")
                print(f"  Memory Operations: {avg_memory:.1f}%")
                
                print(f"\\nCache Performance:")
                print(f"  L1D Miss Rate: {avg_l1d_miss:.3f} ({avg_l1d_miss*100:.1f}%)")
                
                # Detailed breakdown by configuration
                print(f"\\nBy Configuration:")
                for config in ['small', 'medium', 'large']:
                    config_results = [r for r in results if r['config'] == config]
                    if config_results:
                        r = config_results[0]  # Take first result for this config
                        print(f"  {config.capitalize():>6}: IPC={r['ipc']:.3f}, Int={r['Integer_total_pct']:.1f}%, Mem={r['Memory_total_pct']:.1f}%")
        
        # Generate chart data for manual visualization
        self.generate_chart_data()
    
    def generate_chart_data(self):
        """Generate data suitable for creating charts"""
        by_codec = defaultdict(list)
        for r in self.profiling_results:
            by_codec[r['codec']].append(r)
        
        print("\\n" + "="*60)
        print("CHART DATA (for manual visualization)")
        print("="*60)
        
        print("\\nOperation Distribution by Codec:")
        print("Codec\\t\\tInteger%\\tFP+SIMD%\\tMemory%")
        print("-" * 50)
        
        for codec in ['jpeg2k', 'mp3', 'h264']:
            if codec in by_codec:
                results = by_codec[codec]
                avg_integer = sum(r['Integer_total_pct'] for r in results) / len(results)
                avg_fp_simd = sum(r['FP_SIMD_combined_pct'] for r in results) / len(results)
                avg_memory = sum(r['Memory_total_pct'] for r in results) / len(results)
                
                print(f"{codec.upper():12}\\t{avg_integer:6.1f}\\t{avg_fp_simd:7.1f}\\t{avg_memory:6.1f}")
        
        print("\\nIPC by Configuration:")
        print("Codec\\t\\tSmall\\tMedium\\tLarge")
        print("-" * 40)
        
        for codec in ['jpeg2k', 'mp3', 'h264']:
            if codec in by_codec:
                results = by_codec[codec]
                ipc_by_config = {}
                
                for config in ['small', 'medium', 'large']:
                    config_results = [r for r in results if r['config'] == config]
                    if config_results:
                        ipc_by_config[config] = config_results[0]['ipc']
                    else:
                        ipc_by_config[config] = 0.0
                
                print(f"{codec.upper():12}\\t{ipc_by_config['small']:.3f}\\t{ipc_by_config['medium']:.3f}\\t{ipc_by_config['large']:.3f}")
        
        print("\\nWorkload Summary (for DSE selection):")
        print("-" * 50)
        
        recommendations = []
        for codec in ['jpeg2k', 'mp3', 'h264']:
            if codec in by_codec:
                results = by_codec[codec]
                valid_ipcs = [r['ipc'] for r in results if r['ipc'] is not None]
                avg_ipc = sum(valid_ipcs) / len(valid_ipcs) if valid_ipcs else 0
                ipc_range = (max(valid_ipcs) - min(valid_ipcs)) if len(valid_ipcs) > 1 else 0
                avg_integer = sum(r['Integer_total_pct'] for r in results) / len(results)
                avg_memory = sum(r['Memory_total_pct'] for r in results) / len(results)
                
                # Simple scoring for DSE recommendation
                score = 0
                if avg_integer > 50: score += 3
                if avg_memory > 25: score += 2
                if ipc_range > 0.1: score += 2
                if avg_ipc < 0.4: score += 1
                
                recommendations.append((codec, score, avg_ipc, avg_integer, avg_memory))
        
        # Sort by score
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        for i, (codec, score, ipc, integer, memory) in enumerate(recommendations, 1):
            print(f"{i}. {codec.upper()}: Score={score}, IPC={ipc:.3f}, Int={integer:.1f}%, Mem={memory:.1f}%")
            if i == 1:
                print("   --> RECOMMENDED for extensive DSE")

def main():
    print("Multimedia Workload Profiling Analysis")
    print("=====================================")
    
    analyzer = MultimediaProfilingAnalysis()
    analyzer.process_stats_files()
    
    print("\\n" + "="*60)
    print("FILES GENERATED:")
    print("- profiling_results.csv (complete data)")
    print("="*60)

if __name__ == "__main__":
    main()