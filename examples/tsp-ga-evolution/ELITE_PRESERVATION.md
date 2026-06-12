# Elite Preservation en irace-evo

## ¿Qué es Elite Preservation?

Elite preservation es una estrategia que **garantiza que las mejores variantes nunca se pierden** durante el proceso evolutivo. En lugar de reemplazar todas las variantes en cada iteración, el sistema preserve automáticamente la variante con mejor rendimiento.

## Cómo Funciona

### Sin Elite Preservation (comportamiento anterior):
```
Iter1: [Original] + [V0_iter1, V1_iter1, V2_iter1]
       ↓ (irace evalúa: V1 es la mejor con rank 1)
       
Iter2: [Original] + [V0_iter2, V1_iter2, V2_iter2] 
       ↓ (V1_iter1 se pierde para siempre, aunque era buena)
```

### Con Elite Preservation (nuevo comportamiento):
```
Iter1: [Original] + [V0_iter1, V1_iter1, V2_iter1]
       ↓ (irace evalúa: V1_iter1 es la mejor con rank 1)
       
Iter2: [Original] + [V1_iter1_PRESERVADA, V0_iter2, V1_iter2] 
       ↓ (La mejor variante se mantiene + se generan nuevas)
```

## Ventajas

1. **Nunca pierdes progreso**: Las mejores soluciones se mantienen disponibles
2. **Convergencia más estable**: Evita retrocesos en el rendimiento
3. **Aprendizaje incremental**: Cada iteración construye sobre los mejores resultados anteriores

## Implementación Técnica

### En Python (`code_manager.py`):
- Se identifican las variantes por su ranking de irace
- La variante con **menor rank** (mejor rendimiento) se preserve automáticamente
- Las demás variantes están disponibles para evolución/reemplazo

### En R (`code_evolution.R`):
- Las variantes preservadas se marcan con `strategy='elite_preserved'`
- Se guardan con nomenclatura especial: `variant_X_iterY_elite`

## Logs del Sistema

Cuando el sistema preserva una variante elite, verás mensajes como:
```
ELITE PRESERVED: variant_1_iter2 (rank: 1.0)
irace-evo: Elite variant preserved as: variant_0_iter3_elite
```

## Configuración

El sistema está **activado por defecto** y no requiere configuración adicional. El número de variantes preservadas es automáticamente 1 (la mejor de cada iteración).

---

**Resultado**: El sistema ahora nunca perderá las mejores variantes, garantizando que el progreso evolutivo sea siempre incremental y sin retrocesos.