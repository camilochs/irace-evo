# Elite Preservation - Configuración Experimental

## Descripción

Elite Preservation es una funcionalidad de irace-evo que preserva automáticamente las mejores variantes de código entre iteraciones, evitando que se pierdan mejoras evolutivas.

## Configuración

### Activar Elite Preservation (Recomendado)
```json
{
  "llm_config": {
    "elite_preservation": true
  }
}
```

### Desactivar Elite Preservation (Para comparaciones)
```json  
{
  "llm_config": {
    "elite_preservation": false
  }
}
```

## Archivos de Configuración Disponibles

### 1. `code-evolution.json` 
- **Elite preservation**: ✅ **ACTIVADO**
- **Uso**: Producción y experimentos con preservación
- **Comportamiento**: Preserva la mejor variante + genera solo 2 nuevas por iteración

### 2. `code-evolution-NO-elite.json`
- **Elite preservation**: ❌ **DESACTIVADO** 
- **Uso**: Comparaciones experimentales
- **Comportamiento**: Genera 3 nuevas variantes cada iteración (comportamiento clásico)

## Experimentos Comparativos

### Escenario A: Con Elite Preservation
```bash
# Copiar configuración con elite preservation
cp code-evolution.json code-evolution-active.json

# Ejecutar irace-evo
irace --scenario scenario.txt --parameter-file parameters.txt
```

### Escenario B: Sin Elite Preservation  
```bash
# Copiar configuración sin elite preservation
cp code-evolution-NO-elite.json code-evolution.json

# Ejecutar irace-evo
irace --scenario scenario.txt --parameter-file parameters.txt
```

### Escenario C: Comparación A/B
```bash
# Terminal 1: Con Elite Preservation
mkdir experiment-WITH-elite
cd experiment-WITH-elite
cp ../code-evolution.json .
cp ../scenario.txt .
cp ../parameters.txt .
irace --scenario scenario.txt

# Terminal 2: Sin Elite Preservation  
mkdir experiment-WITHOUT-elite
cd experiment-WITHOUT-elite
cp ../code-evolution-NO-elite.json ./code-evolution.json
cp ../scenario.txt .
cp ../parameters.txt .
irace --scenario scenario.txt
```

## Métricas a Comparar

### Efectividad
- **Solution Quality**: Gap respecto al óptimo conocido
- **Convergence Speed**: Iteraciones hasta encontrar mejor solución
- **Final Performance**: Calidad del algoritmo final generado

### Eficiencia
- **LLM API Calls**: Número total de llamadas al LLM
- **Cost per Improvement**: Costo en $ por mejora porcentual
- **Time to Best**: Tiempo hasta encontrar la mejor configuración

### Estabilidad
- **Consistency**: Variabilidad entre runs independientes  
- **Robustness**: Performance en instancias no vistas
- **Progressive Improvement**: Mejora monotónica vs. fluctuaciones

## Interpretación de Resultados

### Elite Preservation ACTIVADO:
```
Iter 1: 3 variantes nuevas (inicial)
Iter 2: 1 preservada + 2 nuevas = 3 total  
Iter 3: 1 preservada + 2 nuevas = 3 total
...
```
- ✅ **Ventajas**: Progreso garantizado, menos LLM calls, convergencia estable
- ⚠️ **Posibles desventajas**: Menos exploración, posible convergencia prematura

### Elite Preservation DESACTIVADO:
```
Iter 1: 3 variantes nuevas
Iter 2: 3 variantes nuevas (reemplazo total)
Iter 3: 3 variantes nuevas (reemplazo total)  
...
```
- ✅ **Ventajas**: Máxima exploración, diversidad genética, evita local optima
- ⚠️ **Posibles desventajas**: Pérdida de progreso, más LLM calls, inestabilidad

## Logs de Verificación

### Con Elite Preservation:
```
INFO:code_manager:Elite preservation enabled: True
INFO:code_manager:ELITE PRESERVATION: Preserving best variant variant_1_iter2
INFO:code_manager:Generated 2 successful variants out of 2 attempts
```

### Sin Elite Preservation:
```
INFO:code_manager:Elite preservation enabled: False
INFO:code_manager:Generated 3 successful variants out of 3 attempts
```

## Análisis de Resultados

### 1. Convergence Plots
```python
import matplotlib.pyplot as plt

# Plot convergencia comparativa
plt.figure(figsize=(12, 6))
plt.subplot(1, 2, 1)
plt.plot(iterations_with_elite, best_costs_with_elite, 'b-', label='With Elite')
plt.plot(iterations_without_elite, best_costs_without_elite, 'r--', label='Without Elite')
plt.xlabel('Iteration')
plt.ylabel('Best Cost Found')
plt.title('Convergence Comparison')
plt.legend()
```

### 2. Cost Analysis
```python
# Análisis costo-beneficio
total_llm_calls_with = len(calls_with_elite)
total_llm_calls_without = len(calls_without_elite)
final_improvement_with = (baseline_cost - final_cost_with_elite) / baseline_cost
final_improvement_without = (baseline_cost - final_cost_without_elite) / baseline_cost

efficiency_with = final_improvement_with / total_llm_calls_with
efficiency_without = final_improvement_without / total_llm_calls_without
```

### 3. Statistical Testing
```r
# Test significancia estadística
t.test(results_with_elite, results_without_elite, paired=TRUE)
wilcox.test(results_with_elite, results_without_elite, paired=TRUE)
```

## Recomendaciones

### Para Investigación:
- **Usar ambas configuraciones** en experimentos A/B
- **10+ runs independientes** por configuración  
- **Métricas múltiples** (no solo solution quality)
- **Análisis estadístico riguroso** con tests de significancia

### Para Producción:
- **Activar Elite Preservation** por defecto
- **Menor costo** en llamadas LLM
- **Mayor estabilidad** y predictibilidad
- **Progreso garantizado** sin retrocesos

### Para Exploración:
- **Desactivar Elite Preservation** cuando se busque máxima novedad
- **Problemas difíciles** donde elite puede estar en local optima
- **Experimentación** con algoritmos completamente nuevos

---

**Nota**: Ambas configuraciones usan los mismos parámetros LLM (model, temperature, etc.) para garantizar comparaciones justas. La única diferencia es el flag `elite_preservation`.