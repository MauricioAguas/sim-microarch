# -*- coding: utf-8 -*-
"""
Análisis del algoritmo Greedy - Arquitectura Avanzada
Autor: Daniel Usme
Fecha: 2025-10-29
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ---------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------
BASE_DIR = "greedy_results"
CSV_FILE = os.path.join(BASE_DIR, "history.csv")

# Cargar el archivo
df = pd.read_csv(CSV_FILE)
print("Columnas detectadas:", df.columns.tolist())
print(df.head(), "\n")

# ---------------------------------------------------------------------
# CONVERSIÓN DE TIPOS NUMÉRICOS
# ---------------------------------------------------------------------
for col in ["EDP", "Energía", "CPI", "Leakage", "RuntimeDynamic"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ---------------------------------------------------------------------
# GRAFICA 1: Evolución del EDP
# ---------------------------------------------------------------------
plt.figure(figsize=(8, 4))
plt.plot(df["Iteración"], df["EDP"], marker="o", linewidth=1.5, color="blue")
plt.title("Evolución del EDP durante la búsqueda Greedy")
plt.xlabel("Iteración")
plt.ylabel("EDP")
plt.grid(True)
plt.tight_layout()
plt.show()

# ---------------------------------------------------------------------
# GRAFICA 2: Tendencia del consumo energético
# ---------------------------------------------------------------------
plt.figure(figsize=(8, 4))
plt.plot(df["Iteración"], df["Energía"], label="Energía total", color="darkgreen")
plt.plot(df["Iteración"], df["Leakage"], label="Leakage", linestyle="--", color="orange")
plt.plot(df["Iteración"], df["RuntimeDynamic"], label="RuntimeDynamic", linestyle="--", color="red")
plt.legend()
plt.title("Tendencia del consumo energético")
plt.xlabel("Iteración")
plt.ylabel("Valor (unidades normalizadas)")
plt.grid(True)
plt.tight_layout()
plt.show()

# ---------------------------------------------------------------------
# GRAFICA 3: Variación del CPI
# ---------------------------------------------------------------------
plt.figure(figsize=(8, 4))
plt.plot(df["Iteración"], df["CPI"], marker="x", color="purple")
plt.title("Variación del CPI durante la búsqueda Greedy")
plt.xlabel("Iteración")
plt.ylabel("CPI")
plt.grid(True)
plt.tight_layout()
plt.show()

# ---------------------------------------------------------------------
# GRAFICA 4: EDP vs Energía (color según parámetro)
# ---------------------------------------------------------------------
plt.figure(figsize=(7, 6))
sns.scatterplot(data=df, x="Energía", y="EDP", hue="Parámetro", palette="tab10", s=80)
plt.title("Espacio de diseño: Energía vs EDP")
plt.xlabel("Energía")
plt.ylabel("EDP")
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()

# ---------------------------------------------------------------------
# GRAFICA 5: Promedio de EDP por parámetro modificado
# ---------------------------------------------------------------------
plt.figure(figsize=(9, 4))
df.groupby("Parámetro")["EDP"].mean().sort_values().plot(kind="bar", color="steelblue")
plt.title("Promedio de EDP por parámetro modificado")
plt.ylabel("EDP promedio")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()

# ---------------------------------------------------------------------
# GRAFICA 6: Frontera de Pareto (Energía vs CPI)
# ---------------------------------------------------------------------
plt.figure(figsize=(7, 6))
sns.scatterplot(data=df, x="Energía", y="CPI", hue="Parámetro", palette="tab10", s=70)
plt.title("Frontera de Pareto: Energía vs CPI")
plt.xlabel("Energía")
plt.ylabel("CPI")
plt.tight_layout()
plt.show()

# ---------------------------------------------------------------------
# RESUMEN DE MEJORES CONFIGURACIONES
# ---------------------------------------------------------------------
print("===== TOP 3 CONFIGURACIONES MÁS EFICIENTES (por EDP) =====")
best = df.nsmallest(3, "EDP")[["Iteración", "Parámetro", "Valor probado", "EDP", "Energía", "CPI", "Configuración completa"]]
print(best.to_string(index=False), "\n")

print("===== TOP 3 CONFIGURACIONES MÁS EFICIENTES EN ENERGÍA =====")
best_energy = df.nsmallest(3, "Energía")[["Iteración", "Parámetro", "Valor probado", "Energía", "CPI", "EDP"]]
print(best_energy.to_string(index=False), "\n")

print("===== TOP 3 CONFIGURACIONES CON MEJOR PERFORMANCE (CPI MÁS BAJO) =====")
best_perf = df.nsmallest(3, "CPI")[["Iteración", "Parámetro", "Valor probado", "CPI", "Energía", "EDP"]]
print(best_perf.to_string(index=False))

# ---------------------------------------------------------------------
# EXPORTAR RESUMEN CSV
# ---------------------------------------------------------------------
output_summary = os.path.join(BASE_DIR, "resumen_greedy.csv")
summary = pd.concat([best, best_energy, best_perf])
summary.to_csv(output_summary, index=False)
print(f"\nResumen exportado a: {output_summary}")

