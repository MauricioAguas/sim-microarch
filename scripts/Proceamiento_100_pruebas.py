import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler

BASE_DIR = "Simulaciones_usme"
CSV_FILE = os.path.join(BASE_DIR, "gem5_summary_stats.csv")

df = pd.read_csv(CSV_FILE)

# Limpieza
for col in df.columns:
    df[col] = pd.to_numeric(df[col], errors="ignore")

# Extraer parámetros desde el nombre de simulación
df["L1i_size"] = df["simulation"].str.extract(r"L1i(\d+kB)")
df["L1d_size"] = df["simulation"].str.extract(r"L1d(\d+kB)")
df["L2_size"] = df["simulation"].str.extract(r"L2(\d+kB)")
df["FW"] = df["simulation"].str.extract(r"FW(\d+)").astype(float)
df["DW"] = df["simulation"].str.extract(r"DW(\d+)").astype(float)
df["CW"] = df["simulation"].str.extract(r"CW(\d+)").astype(float)

# === Crear un puntaje compuesto de eficiencia ===
# Normaliza IPC (alto mejor), CPI (bajo mejor), simSeconds (bajo mejor)
scaler = MinMaxScaler()

df_scaled = df[["system.cpu.ipc", "system.cpu.cpi", "simSeconds"]].copy()
df_scaled = pd.DataFrame(scaler.fit_transform(df_scaled), columns=df_scaled.columns)

df["efficiency_score"] = (
    df_scaled["system.cpu.ipc"] * 0.6 +          # IPC pesa más (rendimiento)
    (1 - df_scaled["system.cpu.cpi"]) * 0.25 +  # penaliza CPI alto
    (1 - df_scaled["simSeconds"]) * 0.15        # favorece menor latencia
)

# === Clasificar en categorías ===
df["performance_label"] = pd.qcut(df["efficiency_score"], 3, labels=["Baja", "Media", "Alta"])

# === Determinar la mejor configuración ===
best_sim = df.loc[df["efficiency_score"].idxmax()]
print("\n=== MEJOR CONFIGURACIÓN ENCONTRADA ===")
print(best_sim[["simulation", "system.cpu.ipc", "system.cpu.cpi", "simSeconds", "efficiency_score", "performance_label"]])
print("\nParámetros asociados:")
print(best_sim[["L1i_size", "L1d_size", "L2_size", "FW", "DW", "CW"]])

# === Generar gráficas ===
plots_dir = os.path.join(BASE_DIR, "graficas_etiquetadas")
os.makedirs(plots_dir, exist_ok=True)

# 1. Distribución del score de eficiencia
plt.figure(figsize=(6,4))
sns.histplot(df["efficiency_score"], bins=20, color="steelblue")
plt.title("Distribución del puntaje de eficiencia")
plt.xlabel("Score de eficiencia")
plt.ylabel("Número de simulaciones")
plt.tight_layout()
plt.savefig(os.path.join(plots_dir, "distribucion_eficiencia.png"), dpi=300)
plt.close()

# 2. IPC vs CPI con etiquetas
plt.figure(figsize=(6,5))
sns.scatterplot(x="system.cpu.cpi", y="system.cpu.ipc", hue="performance_label", data=df, palette={"Alta":"green","Media":"orange","Baja":"red"})
plt.xlabel("CPI")
plt.ylabel("IPC")
plt.title("Rendimiento (IPC vs CPI) con clasificación por eficiencia")
plt.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig(os.path.join(plots_dir, "ipc_vs_cpi_etiquetas.png"), dpi=300)
plt.close()

# 3. Heatmap: L1i vs L2 vs IPC
pivot = df.pivot_table(values="system.cpu.ipc", index="L1i_size", columns="L2_size", aggfunc="mean")
plt.figure(figsize=(6,5))
sns.heatmap(pivot, annot=True, cmap="YlGnBu", fmt=".3f")
plt.title("Promedio IPC según tamaño de cachés L1i y L2")
plt.xlabel("L2 size")
plt.ylabel("L1i size")
plt.tight_layout()
plt.savefig(os.path.join(plots_dir, "ipc_heatmap_caches.png"), dpi=300)
plt.close()

# 4. IPC promedio vs ancho de fetch
plt.figure(figsize=(6,4))
sns.barplot(x="FW", y="system.cpu.ipc", data=df, palette="viridis", errorbar=None)
plt.title("IPC promedio según Fetch Width")
plt.xlabel("Fetch Width")
plt.ylabel("IPC promedio")
plt.tight_layout()
plt.savefig(os.path.join(plots_dir, "ipc_vs_fetchwidth.png"), dpi=300)
plt.close()

# 5. Matriz de correlación con etiquetas legibles
corr = df[["system.cpu.ipc","system.cpu.cpi","simSeconds","hostSeconds","system.cpu.numCycles"]].corr()
plt.figure(figsize=(7,5))
sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
plt.title("Matriz de correlación entre métricas clave")
plt.tight_layout()
plt.savefig(os.path.join(plots_dir, "correlacion_metricas.png"), dpi=300)
plt.close()

print(f"\nGráficas detalladas con etiquetas generadas en: {plots_dir}")
