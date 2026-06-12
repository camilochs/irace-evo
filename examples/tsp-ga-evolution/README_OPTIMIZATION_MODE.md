# Target Runner - Optimization Mode Support

Este target-runner ha sido adaptado para soportar tanto problemas de **minimización** como de **maximización**.

## Cómo Usar

### Para Problemas de Minimización (Default)

```bash
# Ejecución normal - modo minimización por defecto
./target-runner 1 1 12345 instances/berlin52.tsp --population-size 100 --generations 50
```

### Para Problemas de Maximización

```bash
# Configurar variable de entorno para maximización
export MAXIMIZE=1
./target-runner 1 1 12345 instances/berlin52.tsp --population-size 100 --generations 50
```

O alternativamente:

```bash
# En una sola línea
MAXIMIZE=1 ./target-runner 1 1 12345 instances/berlin52.tsp --population-size 100 --generations 50
```

## Funcionamiento Interno

### Modo Minimización (MAXIMIZE=0 o no definido)
- Los costos se devuelven tal como los produce el algoritmo
- Las penalizaciones son números positivos altos (999999)
- irace minimiza directamente el valor devuelto

### Modo Maximización (MAXIMIZE=1)  
- Los costos se devuelven como **valores negativos** (para que irace los minimice)
- Si el algoritmo produce un valor objetivo de 100, el target-runner devuelve -100
- Las penalizaciones son números negativos muy bajos (-999999)
- irace minimiza el valor negativo, efectivamente maximizando el objetivo original

## Ejemplos

### Problema TSP (Minimización)
```bash
# Algoritmo devuelve: 7542 (longitud del tour)
# Target-runner devuelve: 7542 
# irace minimiza: 7542 ✓
```

### Problema de Ganancia (Maximización)
```bash
export MAXIMIZE=1
# Algoritmo devuelve: 150 (ganancia)
# Target-runner devuelve: -150
# irace minimiza: -150 (equivale a maximizar 150) ✓
```

## Validación y Penalizaciones

El script valida que:
- El algoritmo produzca salida válida
- Los valores estén en formato numérico correcto
- No haya valores excesivamente grandes (>1,000,000 en valor absoluto)

### Penalizaciones por Modo

| Situación | Minimización | Maximización |
|-----------|-------------|--------------|
| Timeout   | +999999     | -999999      |
| Error     | +999999     | -999999      |
| Sin salida| +999999     | -999999      |

## Debugging

Para ver información de debug, configurar:

```bash
export DEBUG=1
export MAXIMIZE=1
./target-runner 1 1 12345 instances/test.tsp --param1 value1
```

Esto mostrará:
- Modo de optimización activo
- Costo extraído del algoritmo
- Valor final devuelto a irace