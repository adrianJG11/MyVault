---
name: testing-best-practices
description: Guía pragmática para diseñar, escribir, revisar y ejecutar tests con pytest en aplicaciones Python y FastAPI. Usar al probar lógica, endpoints, PostgreSQL u otras integraciones, al corregir regresiones y antes de considerar terminada una tarea con comportamiento verificable.
---

# Testing Best Practices

Probar comportamiento observable, no detalles internos innecesarios. Priorizar tests pequeños, claros y con nombres que expliquen el comportamiento comprobado.

## Elegir el alcance

- Usar unit tests para lógica aislada.
- Usar integration tests cuando importe verificar FastAPI, PostgreSQL u otros componentes trabajando juntos.
- Cubrir el happy path y los errores relevantes.
- Añadir un test de regresión al corregir un bug importante.
- No perseguir 100 % de coverage únicamente para alcanzar una cifra.

## Mantener los tests

- No mockear todo por defecto ni acoplar excesivamente los tests a la implementación.
- Usar fixtures cuando reduzcan duplicación real.
- No construir sistemas grandes de fixtures prematuramente.
- Mantener cada test enfocado y fácil de entender.

## Verificar

Ejecutar los tests relevantes antes de considerar terminada la tarea. Si un test falla, investigar primero la causa; no modificarlo solo para hacerlo pasar.
