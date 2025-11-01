
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from collections import defaultdict

# Set style for better looking plots
plt.style.use('default')
sns.set_palette("husl")

class ProfilingVisualizer:
    def __init__(self, csv_file):
        """Load CSV data"""
        self.df = pd.read_csv(csv_file)
        print(f"Loaded {len(self.df)} profiling results")
        print(f"Codecs: {sorted(self.df['codec'].unique())}")
        print(f"Configurations: {sorted(self.df['config'].unique())}")
    
    def create_comprehensive_charts(self):
        """Create all profiling charts"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Chart 1: Operation Distribution by Codec
        self.plot_operation_distribution(ax1)
        
        # Chart 2: IPC Performance by Configuration
        self.plot_ipc_performance(ax2)
        
        # Chart 3: Cache Miss Rates
        self.plot_cache_miss_rates(ax3)
        
        # Chart 4: Workload Comparison
        self.plot_workload_comparison(ax4)
        
        plt.suptitle('Multimedia Workload Profiling Results', fontsize=16, y=0.98)
        plt.tight_layout()
        plt.show()
        
        # Additional individual charts
        self.plot_detailed_breakdown()
        self.plot_configuration_sensitivity()
    
    def plot_operation_distribution(self, ax):
        """Chart 1: Operation distribution by codec"""
        codecs = ['jpeg2k', 'mp3', 'h264']
        codec_labels = ['JPEG2000', 'MP3', 'H.264']
        
        # Calculate averages by codec
        operation_data = {}
        for codec in codecs:
            codec_df = self.df[self.df['codec'] == codec]
            operation_data[codec] = {
                'Integer': codec_df['Integer_total_pct'].mean(),
                'FP+SIMD': codec_df['FP_SIMD_combined_pct'].mean(),
                'Memory': codec_df['Memory_total_pct'].mean()
            }
        
        # Create grouped bar chart
        x_pos = np.arange(len(codecs))
        width = 0.25
        colors = ['#3498db', '#e74c3c', '#f39c12']
        
        for i, (op_type, color) in enumerate(zip(['Integer', 'FP+SIMD', 'Memory'], colors)):
            values = [operation_data[codec][op_type] for codec in codecs]
            bars = ax.bar(x_pos + i*width, values, width, label=op_type, color=color, alpha=0.8)
            
            # Add value labels
            for bar, value in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                       f'{value:.1f}%', ha='center', va='bottom', fontsize=9)
        
        ax.set_xlabel('Multimedia Codecs')
        ax.set_ylabel('Percentage of Operations (%)')
        ax.set_title('Operation Distribution by Codec')
        ax.set_xticks(x_pos + width)
        ax.set_xticklabels(codec_labels)
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
    
    def plot_ipc_performance(self, ax):
        """Chart 2: IPC performance by configuration"""
        codecs = ['jpeg2k', 'mp3', 'h264']
        codec_labels = ['JPEG2000', 'MP3', 'H.264']
        configs = ['small', 'medium', 'large']
        colors = ['#3498db', '#e74c3c', '#2ecc71']
        
        for codec_idx, codec in enumerate(codecs):
            codec_df = self.df[self.df['codec'] == codec]
            ipc_by_config = []
            
            for config in configs:
                config_df = codec_df[codec_df['config'] == config]
                avg_ipc = config_df['ipc'].mean() if len(config_df) > 0 else 0
                ipc_by_config.append(avg_ipc)
            
            ax.plot(configs, ipc_by_config, marker='o', linewidth=2.5, 
                   label=codec_labels[codec_idx], color=colors[codec_idx], markersize=8)
        
        ax.set_xlabel('Configuration Size')
        ax.set_ylabel('IPC (Instructions per Cycle)')
        ax.set_title('IPC Performance by Configuration')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def plot_cache_miss_rates(self, ax):
        """Chart 3: Cache miss rates"""
        codecs = ['jpeg2k', 'mp3', 'h264']
        codec_labels = ['JPEG2000', 'MP3', 'H.264']
        
        cache_data = {}
        for codec in codecs:
            codec_df = self.df[self.df['codec'] == codec]
            cache_data[codec] = {
                'L1D': codec_df['l1d_miss_rate'].mean() * 100,
                'L1I': codec_df['l1i_miss_rate'].mean() * 100,
                'L2': codec_df['l2_miss_rate'].mean() * 100
            }
        
        x_pos = np.arange(len(codecs))
        width = 0.25
        colors = ['#9b59b6', '#1abc9c', '#f1c40f']
        
        for i, (cache_type, color) in enumerate(zip(['L1D', 'L1I', 'L2'], colors)):
            values = [cache_data[codec][cache_type] for codec in codecs]
            bars = ax.bar(x_pos + i*width, values, width, label=f'{cache_type} Miss Rate', 
                         color=color, alpha=0.8)
            
            # Add value labels
            for bar, value in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                       f'{value:.1f}%', ha='center', va='bottom', fontsize=9)
        
        ax.set_xlabel('Multimedia Codecs')
        ax.set_ylabel('Miss Rate (%)')
        ax.set_title('Cache Miss Rates by Codec')
        ax.set_xticks(x_pos + width)
        ax.set_xticklabels(codec_labels)
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def plot_workload_comparison(self, ax):
        """Chart 4: Detailed workload comparison"""
        workloads = sorted(self.df['workload'].unique())
        workload_labels = [wl.replace('_', '\\n') for wl in workloads]
        
        ipc_values = []
        integer_values = []
        memory_values = []
        
        for wl in workloads:
            wl_df = self.df[self.df['workload'] == wl]
            ipc_values.append(wl_df['ipc'].mean())
            integer_values.append(wl_df['Integer_total_pct'].mean())
            memory_values.append(wl_df['Memory_total_pct'].mean())
        
        x_workloads = np.arange(len(workloads))
        
        bars1 = ax.bar(x_workloads - 0.2, integer_values, 0.4, label='Integer %', 
                      color='#3498db', alpha=0.8)
        bars2 = ax.bar(x_workloads + 0.2, memory_values, 0.4, label='Memory %', 
                      color='#f39c12', alpha=0.8)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, height + 1,
                       f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
        
        ax.set_xlabel('Workloads')
        ax.set_ylabel('Percentage (%)')
        ax.set_title('Integer vs Memory Distribution by Workload')
        ax.set_xticks(x_workloads)
        ax.set_xticklabels(workload_labels, fontsize=9)
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def plot_detailed_breakdown(self):
        """Additional detailed breakdown charts"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Detailed operation breakdown
        codecs = ['jpeg2k', 'mp3', 'h264']
        codec_labels = ['JPEG2000', 'MP3', 'H.264']
        
        # Chart 1: Detailed operations
        operations = ['IntAlu_pct', 'MemRead_pct', 'MemWrite_pct', 'Float_total_pct', 'Simd_total_pct']
        op_labels = ['IntALU', 'Mem Read', 'Mem Write', 'Float', 'SIMD']
        
        x_pos = np.arange(len(codecs))
        width = 0.15
        colors = plt.cm.Set3(np.linspace(0, 1, len(operations)))
        
        for i, (op, label, color) in enumerate(zip(operations, op_labels, colors)):
            values = []
            for codec in codecs:
                codec_df = self.df[self.df['codec'] == codec]
                avg_val = codec_df[op].mean() if op in codec_df.columns else 0
                values.append(avg_val)
            
            bars = ax1.bar(x_pos + i*width, values, width, label=label, color=color, alpha=0.8)
            
            # Add small value labels for non-zero values
            for bar, value in zip(bars, values):
                if value > 2:  # Only label if > 2%
                    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                           f'{value:.1f}', ha='center', va='bottom', fontsize=8)
        
        ax1.set_xlabel('Multimedia Codecs')
        ax1.set_ylabel('Percentage (%)')
        ax1.set_title('Detailed Operation Breakdown by Codec')
        ax1.set_xticks(x_pos + width * len(operations) / 2)
        ax1.set_xticklabels(codec_labels)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Chart 2: Configuration sensitivity
        configs = ['small', 'medium', 'large']
        metrics = ['ipc', 'Integer_total_pct', 'Memory_total_pct']
        metric_labels = ['IPC', 'Integer %', 'Memory %']
        
        for codec_idx, codec in enumerate(codecs):
            codec_df = self.df[self.df['codec'] == codec]
            
            # Normalize metrics for comparison (0-1 scale)
            normalized_data = []
            for metric in metrics:
                config_values = []
                for config in configs:
                    config_df = codec_df[codec_df['config'] == config]
                    value = config_df[metric].mean() if len(config_df) > 0 else 0
                    config_values.append(value)
                
                # Normalize to 0-1 scale
                if max(config_values) > 0:
                    normalized = [v/max(config_values) for v in config_values]
                else:
                    normalized = config_values
                normalized_data.append(normalized)
            
            # Plot as grouped lines
            x_config = np.arange(len(configs))
            colors_norm = ['#3498db', '#e74c3c', '#2ecc71']
            
            for metric_idx, (norm_values, label, color) in enumerate(zip(normalized_data, metric_labels, colors_norm)):
                ax2.plot(x_config, norm_values, marker='o', label=f'{codec_labels[codec_idx]} {label}', 
                        color=color, linestyle=['--', '-.', '-'][codec_idx], alpha=0.7, linewidth=2)
        
        ax2.set_xlabel('Configuration')
        ax2.set_ylabel('Normalized Value (0-1)')
        ax2.set_title('Configuration Sensitivity (Normalized)')
        ax2.set_xticks(x_config)
        ax2.set_xticklabels(configs)
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_configuration_sensitivity(self):
        """Sensitivity analysis chart"""
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        codecs = ['jpeg2k', 'mp3', 'h264']
        codec_labels = ['JPEG2000', 'MP3', 'H.264']
        configs = ['small', 'medium', 'large']
        colors = ['#3498db', '#e74c3c', '#2ecc71']
        
        # Create sensitivity heatmap data
        sensitivity_data = []
        for codec in codecs:
            codec_df = self.df[self.df['codec'] == codec]
            codec_row = []
            
            for config in configs:
                config_df = codec_df[codec_df['config'] == config]
                if len(config_df) > 0:
                    # Use IPC as main sensitivity metric
                    ipc_val = config_df['ipc'].mean()
                    codec_row.append(ipc_val)
                else:
                    codec_row.append(0)
            
            sensitivity_data.append(codec_row)
        
        # Create heatmap
        im = ax.imshow(sensitivity_data, cmap='RdYlBu_r', aspect='auto')
        
        # Add text annotations
        for i, codec in enumerate(codec_labels):
            for j, config in enumerate(configs):
                text = ax.text(j, i, f'{sensitivity_data[i][j]:.3f}',
                              ha="center", va="center", color="black", fontweight='bold')
        
        ax.set_xticks(np.arange(len(configs)))
        ax.set_yticks(np.arange(len(codec_labels)))
        ax.set_xticklabels(configs)
        ax.set_yticklabels(codec_labels)
        ax.set_xlabel('Configuration Size')
        ax.set_ylabel('Multimedia Codecs')
        ax.set_title('IPC Sensitivity Heatmap')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('IPC Value', rotation=270, labelpad=20)
        
        plt.tight_layout()
        plt.show()
    
    def print_summary_table(self):
        """Print summary table"""
        print("\\n" + "="*80)
        print("PROFILING SUMMARY TABLE")
        print("="*80)
        
        summary_df = self.df.groupby(['codec', 'config']).agg({
            'ipc': 'mean',
            'Integer_total_pct': 'mean',
            'FP_SIMD_combined_pct': 'mean',
            'Memory_total_pct': 'mean',
            'l1d_miss_rate': 'mean'
        }).round(3)
        
        print(summary_df.to_string())
        
        # Overall codec averages
        print("\\n" + "="*80)
        print("CODEC AVERAGES")
        print("="*80)
        
        codec_avg = self.df.groupby('codec').agg({
            'ipc': 'mean',
            'Integer_total_pct': 'mean',
            'FP_SIMD_combined_pct': 'mean',
            'Memory_total_pct': 'mean',
            'l1d_miss_rate': 'mean'
        }).round(3)
        
        print(codec_avg.to_string())



def main():
    # Load the CSV file (adjust filename if needed)
    try:
        visualizer = ProfilingVisualizer('profiling_results.csv')
        
        # Generate all charts
        print("Generating comprehensive profiling charts...")
        visualizer.create_comprehensive_charts()
        
        # Print summary table
        visualizer.print_summary_table()
        
        print("\\nVisualization complete!")
        print("Charts displayed above show:")
        print("1. Operation distribution by codec")
        print("2. IPC performance by configuration")
        print("3. Cache miss rates comparison")
        print("4. Workload-specific breakdowns")
        
    except FileNotFoundError:
        print("ERROR: 'profiling_results.csv' not found!")
        print("Please upload your CSV file to Colab first.")
    except Exception as e:
        print(f"Error: {e}")

# Run the visualization
if __name__ == "__main__":
    main()