---
name: financial-app-security
description: Seguridad proporcionada y secure-by-default para diseñar, implementar o revisar una aplicación local-first que procesa datos financieros personales. Usar con almacenamiento, importación de archivos, autenticación, secretos, logs, bases de datos, contenedores, redes, cifrado, dependencias o cualquier cambio que pueda aumentar la superficie de ataque.
---

# Financial App Security

Aplicar seguridad por defecto con medidas proporcionales a una aplicación personal local-first. Identificar riesgos razonables sin convertirla innecesariamente en un sistema bancario empresarial.

## Datos y secretos

- Minimizar los datos almacenados.
- No guardar credenciales bancarias si no son necesarias ni IBAN completos si bastan identificadores parciales.
- Nunca guardar secretos en Git, imágenes Docker o logs.
- No registrar contraseñas, tokens, credenciales, números completos de cuenta ni datos financieros innecesarios.
- Evitar exponer stack traces, detalles internos o datos sensibles al cliente.

## Entradas y acceso

- Validar toda entrada externa y tratar CSV, Excel y otros archivos importados como no confiables.
- Prevenir path traversal y cargas de archivos inesperados.
- Usar correctamente queries parametrizadas u ORM.
- Aplicar mínimo privilegio a usuarios y servicios.
- No exponer públicamente PostgreSQL ni servicios internos.
- Hacer que la aplicación solo sea accesible localmente por defecto.

## Criptografía, red y dependencias

- No implementar criptografía propia; usar librerías establecidas cuando sea necesario.
- Antes de aplicar cifrado, explicar qué amenaza concreta mitiga.
- Revisar dependencias y mantenerlas actualizadas.
- Señalar explícitamente cualquier cambio que aumente la superficie de ataque.
- Antes de recomendar exposición a Internet, advertir sus implicaciones y proponer alternativas privadas como una VPN.
