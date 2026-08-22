---
name: docker-devops-best-practices
description: Buenas prácticas pragmáticas para diseñar, implementar y revisar Docker, Docker Compose y DevOps en un proyecto personal local-first desarrollado en WSL. Usar con Dockerfiles, Compose, imágenes, redes, volúmenes, secretos, healthchecks, puertos, despliegues y CI/CD.
---

# Docker / DevOps Best Practices

Preferir Docker Compose a Kubernetes mientras no exista una necesidad real. Explicar qué problema concreto resuelve cualquier herramienta nueva antes de añadirla.

## Imágenes y procesos

- Crear imágenes reproducibles y razonablemente pequeñas.
- Usar `.dockerignore` y Dockerfiles sencillos.
- No copiar secretos dentro de imágenes.
- Ejecutar procesos como usuario non-root cuando sea razonable.
- Evitar scripts de shell complejos cuando Docker o Compose ya resuelvan el problema.

## Runtime local

- Usar variables de entorno sin duplicar configuración innecesariamente.
- Definir volúmenes explícitos para datos persistentes.
- Añadir healthchecks cuando tengan utilidad operacional.
- Separar redes internas de puertos publicados.
- No publicar PostgreSQL, Redis u otros servicios internos al host sin una necesidad concreta.
- Publicar aplicaciones locales únicamente en `127.0.0.1` cuando sea suficiente.

## Evolución

- Añadir CI/CD gradualmente.
- Incluir en CI formato/lint, tests, build y security scanning cuando corresponda.
- No introducir Terraform, Kubernetes, Helm u otras herramientas sin un objetivo de aprendizaje o una necesidad concreta.
