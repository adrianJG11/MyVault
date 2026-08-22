---
name: python-fastapi-best-practices
description: Buenas prácticas pragmáticas para diseñar, implementar y revisar aplicaciones con Python moderno, FastAPI, Pydantic, uv y Ruff. Usar al trabajar en endpoints, modelos, validación, configuración, dependencias, lógica de negocio, manejo de errores, concurrencia o estructura del backend Python.
---

# Python + FastAPI Best Practices

Escribir Python moderno, legible y con type hints. Preferir soluciones idiomáticas de Python a patrones trasladados innecesariamente desde Java o C#.

## Diseño de la aplicación

- Usar Pydantic para validar entradas y salidas.
- Organizar endpoints con `APIRouter` y, cuando el proyecto crezca, preferir una estructura por funcionalidad.
- Separar HTTP de lógica de negocio solo cuando exista suficiente lógica para justificarlo.
- No crear capas adicionales prematuramente.
- Usar la inyección de dependencias de FastAPI cuando aporte una ventaja concreta.
- Evitar estado global mutable y mantener el código compatible con tests.

## API y ejecución

- Elegir status codes HTTP correctos y response models explícitos cuando corresponda.
- Manejar excepciones coherentemente sin exponer errores internos, stack traces ni información sensible.
- Usar `async def` solo si el código invocado es realmente asíncrono o existe una razón técnica.
- No bloquear el event loop con operaciones síncronas costosas.
- Configurar mediante variables de entorno y Pydantic Settings cuando sea necesario.

## Herramientas del proyecto

- Usar Ruff para linting y formato, y uv para dependencias y ejecución.
- Mantener `pyproject.toml` y `uv.lock`.
- No crear `requirements.txt` salvo una necesidad explícita de compatibilidad.

## Revisión

Clasificar cada observación como error real, posible mejora o preferencia de estilo. No presentar preferencias personales como reglas obligatorias.
