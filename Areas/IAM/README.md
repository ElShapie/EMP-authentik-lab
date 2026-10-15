# IAM: authentik, OIDC, MFA y aprovisionamiento SCIM 2.0

Esta copia privada usa authentik Open Source como alternativa técnica a OneLogin. El repositorio fuente y su rama `main` permanecen sin cambios; aquí, `main` contiene la variante authentik. La guía original `docs/Guias/04_IAM_OneLogin.md` se conserva como referencia. Como los requisitos del curso declaran OneLogin obligatorio, Dirección debe obtener aprobación del profesor antes de presentar la alternativa.

La aplicación ofrece OIDC por Authorization Code y un receptor SCIM 2.0 con token Bearer estático. Los permisos los decide y revalida la aplicación, no los claims del navegador. La implementación soporta usuarios, filtros por `userName`/`externalId`, lectura, alta, sustitución, PATCH, baja, y discovery SCIM. No sincroniza grupos ni modifica Microsoft 365.

## Guía de configuración

Sigue la [guía paso a paso de IAM/authentik](../../docs/Guias/04_IAM_Authentik.md). La VM de authentik debe ser independiente del Hub y dimensionarse mediante una prueba; no publiques sus puertos internos ni el de SQLite.

El Hub recibe SCIM en `APP_BASE_URL/scim/v2`. El valor `SCIM_TOKEN` generado en el `.env` local del Hub se copia al campo de autenticación estática del proveedor SCIM de authentik. El secreto se comparte por un canal privado y nunca se incluye en archivos versionados, capturas o comandos visibles.

## Perfiles de práctica

| Identificador de laboratorio | Atributo `lab_role` | Función de aplicación |
|---|---|---|
| EMP-001 | `mantenimiento` | Consulta y mantenimiento controlado |
| EMP-002 | `admin` | Administración del Hub |
| EMP-003 | `auditor` | Consulta y registros |
| EMP-004 | `soc` | Eventos e incidentes |
| EMP-005 | `consulta` | Consulta únicamente |
| EMP-006 | `sin_acceso` | Sin funciones protegidas |

Los valores son ejemplos. En la instancia se asignan identificadores EMP autorizados, sin nombres reales en documentos públicos. Añade los atributos `lab_role` y `emp_id` a los usuarios de prueba y asegúrate de que `userName`/correo coincide con la claim `email` devuelta por OIDC.

## Comprobación de SCIM

El verificador solo lee la lista de usuarios y prueba que el endpoint rechace acceso anónimo:

```bash
set -a
source ~/lab-runtime/app/.env
set +a
python3 Areas/IAM/comprobar_scim.py --url https://HUB-HTTPS --scim-version 2
```

Resultado esperado: acceso anónimo `401`, acceso autenticado `200` y `correcto: true`. Nunca incluyas el token en `--url`, en la línea de comandos o en evidencias.

## Pruebas funcionales pendientes de la instancia real

1. Usuario en el grupo autorizado: autentica por OIDC y aparece por SCIM.
2. `lab_role` cambia de `mantenimiento` a `auditor`: la sesión previa recibe `403` en mantenimiento.
3. `active=false`: las operaciones del usuario quedan denegadas.
4. Retirar el acceso al vínculo/grupo de la aplicación: revisar el comportamiento de desprovisionamiento SCIM y que la cuenta no pueda volver a entrar.
5. Usuario fuera del grupo autorizado: no debe sincronizarse ni iniciar sesión.
6. Probar MFA y recuperación según el flujo institucional aprobado.

No se ha conectado aquí una instancia real de authentik. Las pruebas automatizadas usan proveedores simulados y no demuestran OIDC, MFA ni sincronización externa.
