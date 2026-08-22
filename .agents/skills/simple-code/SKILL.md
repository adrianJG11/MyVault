---
name: simple-code
description: Guía para aplicar YAGNI y evitar sobreingeniería al diseñar, implementar, revisar o refactorizar código. Usar cuando una tarea pueda introducir abstracciones, capas, dependencias, configuración o código nuevo, y al comprobar que una solución cumple el requisito actual con la menor complejidad razonable.
---

# Simple Code

Aplicar YAGNI. Preferir la solución explícita, legible y más sencilla que cumpla el requisito actual.

## Antes de escribir

- Inspeccionar el proyecto y reutilizar funcionalidad existente antes de crear código nuevo.
- No duplicar soluciones existentes ni refactorizar código ajeno a la tarea.
- No diseñar para necesidades hipotéticas ni hacer configuración prematura.
- No añadir dependencias si Python, FastAPI o las dependencias actuales resuelven el problema razonablemente.

## Al diseñar e implementar

- No crear interfaces, repositories, factories, managers, helpers ni capas adicionales sin un problema actual concreto.
- Evitar funciones, clases o módulos vacíos preparados para el futuro.
- Mantener funciones pequeñas cuando mejore la legibilidad, sin fragmentarlas artificialmente.
- Preferir código explícito frente a patrones sofisticados.
- No crear una abstracción si añade más complejidad de la que elimina.
- Al proponer una arquitectura más compleja, explicar qué problema concreto actual resuelve.
- Evitar comentarios que solo repitan una línea evidente.

## Comprobación final

Antes de terminar, buscar código, configuración, abstracciones y dependencias que puedan eliminarse sin perder funcionalidad.
