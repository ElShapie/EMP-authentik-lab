# Guía IAM: authentik Open Source para Security Hub

## Alcance y decisión del curso

Esta guía corresponde a la copia privada `EMP-authentik-lab`, cuya rama `main` contiene la variante authentik. El repositorio fuente conserva OneLogin y no se modifica. El documento original de requisitos marca OneLogin como obligatorio; solicita primero autorización explícita del profesor y registra la decisión. No presentes la variante como equivalente aprobado sin esa autorización.

El diseño usa authentik para autenticar por OIDC y empujar el ciclo de vida de usuarios a Security Hub mediante SCIM 2.0. No incluye contraseñas locales, no cambia los permisos internos, no sincroniza Microsoft 365 y no configura las cámaras ni el lector RFID.

## Arquitectura y límites

```text
Navegador ── OIDC Authorization Code ──> authentik
    │                                      │
    └── Security Hub (Flask) <── SCIM 2.0 ─┘
          SQLite privada       token Bearer estático
          permisos por rol     TLS entre servidores
```

- Hub: conserva el login de servidor, sesión segura, roles internos, verificación por operación y vínculo persistente del `sub`.
- authentik: administra identidades, MFA, grupo autorizado y las asignaciones de aplicación.
- SCIM: envía `userName`, `externalId`, `title` y `active`. `title` recibe el valor de `lab_role`; el Hub convierte ese valor en permisos mediante su matriz actual.
- No se aceptan roles desde JavaScript ni se depende del ocultamiento de botones.
- Esta rama conserva `/scim/v1` por compatibilidad, pero authentik debe usar `/scim/v2`.

La versión Open Source de authentik incluye OIDC y SCIM. Su proveedor SCIM admite autenticación por token estático; la autenticación OAuth del proveedor SCIM aparece como función Enterprise. Por eso el ejemplo usa el token generado por el Hub y no supone una licencia pagada. El token es de alto privilegio: almacénalo como secreto y limítalo a este sistema.

## Antes de empezar

Necesitas:

1. Aprobación del profesor para la alternativa OneLogin → authentik.
2. Una VM/laptop de IAM con Docker Compose y espacio persistente para authentik/PostgreSQL. El tamaño de `VM-IAM-01` queda por dimensionar mediante prueba; no se presume que la VM del Hub soporte ambos servicios.
3. Un nombre DNS estable y HTTPS válido para authentik y para el Hub. Los callbacks OIDC y el SCIM servidor-a-servidor no deben depender de URLs temporales que cambien.
4. Acceso administrativo autorizado a la instancia. Limita usuarios sincronizados a un grupo de laboratorio.
5. Una instalación de la versión estable seleccionada siguiendo la [guía oficial Docker Compose](https://docs.goauthentik.io/install-config/install/docker-compose/). Fija y registra la versión del contenedor; no uses una etiqueta flotante `latest` para el ensayo.
6. Un respaldo privado del Hub. No apuntes esta variante al volumen del despliegue OneLogin.

authentik mantiene su propia base PostgreSQL y sus volúmenes. No expongas PostgreSQL, Redis si aplica a la versión, ni el puerto interno del Hub a redes públicas. Publica solo los endpoints HTTPS necesarios por el proxy que ya utilice la infraestructura.

## Paso 1: preparar authentik

1. Instala authentik en `VM-IAM-01` con su documentación oficial y guarda la configuración/secretos fuera del repositorio.
2. Configura HTTPS con certificado válido y comprueba que desde la VM Hub se descarga el documento OIDC sin desafío interactivo de firewall/proxy.
3. Conserva respaldos de PostgreSQL y de los secretos de instalación conforme al procedimiento privado de TI.
4. Crea un grupo dedicado, por ejemplo `Security-Hub-Lab`, y agrega solo las cuentas ficticias autorizadas.
5. Configura MFA en el flujo de autenticación (TOTP o WebAuthn según los dispositivos disponibles) y prueba recuperación. No guardes códigos de recuperación ni QR de inscripción en Git o capturas.
6. No sincronices usuarios externos al grupo. authentik documenta que, si no hay usuarios vinculados al aplicativo SCIM, puede sincronizar todos los usuarios; valida la restricción antes de habilitar el provider.

## Paso 2: configurar OIDC para el Hub

En authentik, abre **Applications → Applications → New Application** y crea la aplicación `Security Hub` con provider **OAuth2/OIDC**. Configura:

1. Tipo de cliente confidencial para una aplicación del lado servidor.
2. Flujo **Authorization Code**; no habilites Implicit ni Password Grant.
3. URI de redirección exacta: `https://DOMINIO_DEL_HUB/auth/callback`.
4. Scopes: `openid`, `profile`, `email`; confirma que el scope `email` publica una claim `email` en UserInfo.
5. Mantén el issuer predeterminado por proveedor y anota el issuer del documento de discovery.
6. Asocia el grupo autorizado al aplicativo mediante bindings/policies.

La metadata URL de authentik tiene la forma:

```text
https://DOMINIO_AUTHENTIK/application/o/SLUG_DE_LA_APLICACION/.well-known/openid-configuration
```

Configura el `.env` privado que preparó TI, dentro de `~/lab-runtime/app`:

```dotenv
OIDC_PROVIDER_NAME=authentik
OIDC_CLIENT_ID=valor_privado_del_provider
OIDC_CLIENT_SECRET=secreto_privado_del_provider
OIDC_METADATA_URL=https://DOMINIO_AUTHENTIK/application/o/security-hub/.well-known/openid-configuration
```

No copies valores reales en documentación, GitHub, tickets, terminales grabadas ni capturas. Reinicia solo el contenedor local del Hub después de cambiar su `.env`; no se requieren migraciones SQL.

## Paso 3: configurar cuentas y roles

1. Crea cuentas de prueba en authentik. Usa correo de laboratorio y registros RR. HH. autorizados; no inventes nombres de personas para ejemplos públicos.
2. Añade los atributos personalizados `lab_role` y `emp_id`.
3. Asigna a `lab_role` exactamente uno de los roles internos existentes: `admin`, `ti`, `seguridad_fisica`, `soc`, `auditor`, `mantenimiento`, `consulta` o `sin_acceso`.
4. Asigna a `emp_id` un identificador `EMP-###` aprobado. No pongas el nombre del puesto/persona en ese campo.
5. El correo OIDC `email` y SCIM `userName` deben coincidir. El callback busca la cuenta aprovisionada por ese correo.
6. Da acceso a la aplicación OIDC únicamente al grupo autorizado.

## Paso 4: configurar SCIM 2.0 de salida

1. En el `.env` privado del Hub, toma `SCIM_TOKEN` por un canal seguro. Es distinto de `APP_SECRET`, `DEVICE_TOKEN` y `CARD_PEPPER`.
2. En authentik crea una aplicación/provider de tipo **SCIM** y elige autenticación **Static token**.
3. Usa como URL/base SCIM `https://DOMINIO_DEL_HUB/scim/v2` y pega el token del Hub en el campo secreto del provider.
4. Asocia el provider SCIM como backchannel del aplicativo OIDC que controla el grupo permitido. Confirma en la UI que solo se sincronice ese grupo; no dejes la aplicación sin bindings.
5. Deja deshabilitada la sincronización de grupos. Esta integración solo implementa ciclo de vida de usuarios; `GET /Groups` responde una lista vacía.
6. Configura una propiedad SCIM para enviar los atributos de la cuenta. El formato debe incluir el esquema Core 2.0 y al menos estos campos:

```python
return {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "userName": request.user.email.lower(),
    "displayName": request.user.name,
    "emails": [{"value": request.user.email.lower(), "type": "work", "primary": True}],
    "active": request.user.is_active,
    "title": request.user.attributes.get("lab_role", "sin_acceso"),
    "externalId": request.user.attributes.get("emp_id", ""),
}
```

En el editor de authentik, verifica la expresión con la versión instalada y los atributos de una cuenta de prueba. Si `email` puede estar vacío, exige que RR. HH. complete la cuenta antes de asignarla al aplicativo. Las propiedades SCIM se validan antes de sincronizar; revisa eventos de authentik después de guardar el mapping.

authentik normalmente sincroniza cambios y también ejecuta una sincronización completa periódica. No confundas ese ciclo con una actualización periódica de la aplicación: el Hub actualiza su cuenta cuando recibe el evento SCIM.

## Paso 5: preparar la instancia aislada del Hub

Esta rama no debe compartir el volumen `app-data` con la versión OneLogin. El almacén actual guarda el `sub` OIDC y rechaza que una cuenta ya vinculada se vuelva a asociar a otro sujeto. Esta salvaguarda evita apropiación por una coincidencia de correo.

1. Conserva intactos el repo/commit y la base de OneLogin.
2. Clona esta copia privada (`https://github.com/ElShapie/EMP-authentik-lab.git`) en una VM de prueba; su rama `main` contiene la variante authentik.
3. Crea un `APP_DB`/volumen nuevo para la prueba; nunca borres ni reemplaces el original para forzar el login.
4. Configura el `.env` con los datos privados de OIDC y deja `APP_BASE_URL` en HTTPS.
5. Inicia el Hub, revisa `docker compose ps`, `/health` y los logs sin imprimir variables de entorno.
6. Espera a que la cuenta de prueba aparezca mediante SCIM y después inicia OIDC.

Una futura migración de usuarios ya existentes requiere plan autorizado de exportación/copia, mapeo de cuentas, tarjetas y auditoría y una decisión segura para el vínculo OIDC; esta rama no resetea `oidc_sub` ni importa datos automáticamente.

## Paso 6: verificar el protocolo y los permisos

Desde el clon del repositorio, en una terminal local protegida:

```bash
set -a
source ~/lab-runtime/app/.env
set +a
python3 Areas/IAM/comprobar_scim.py --url https://DOMINIO_DEL_HUB --scim-version 2
```

Prueba en authentik y el Hub usando solo cuentas ficticias autorizadas:

| Prueba | Resultado esperado |
|---|---|
| `GET /scim/v2/Users` sin token | HTTP 401 |
| `GET /scim/v2/Users` con token | HTTP 200, ListResponse SCIM 2.0 |
| Alta de usuario | HTTP 201, respuesta incluye `id` y Location `/scim/v2/Users/{id}` |
| Correo de usuario y claim OIDC coinciden | Login permite entrar tras aprovisionamiento |
| Usuario no aprovisionado/inactivo | Login denegado |
| Rol `mantenimiento` pasa a `auditor` | Acción de mantenimiento devuelve 403 incluso con sesión anterior |
| Suspender o retirar cuenta | SCIM actualiza `active=false` o elimina; Hub deniega operaciones y bloquea tarjetas vinculadas |
| Usuario fuera de la aplicación/grupo | No sincronizado ni autorizado |
| MFA | Desafío real según política antes de acceder |

Registra hora y resultado sin capturar tokens, correos reales, nombres ni atributos privados. La prueba local automatizada no certifica el tenant ni el factor MFA.

## Recuperación y errores frecuentes

| Síntoma | Revisión segura |
|---|---|
| Callback termina en 403 | Revisar que SCIM ya creó el usuario, que está activo, que `userName` coincide con `email`, y que el sujeto OIDC no está vinculado a otro proveedor |
| Error `invalid_redirect_uri` | Comparar el redirect exacto `APP_BASE_URL/auth/callback`, incluido HTTPS y barra final |
| OIDC metadata/JWKS no carga | Desde la VM Hub, comprobar DNS, certificado, proxy/WAF y el URL de discovery; permitir esas rutas concretas sin desafío interactivo |
| SCIM devuelve 401 | Rotar/comparar `SCIM_TOKEN` por canal privado y revisar que authentik use Static token con `Bearer`; nunca pegar el secreto en un comando |
| SCIM devuelve 400 | Revisar schema SCIM 2.0, mapping, correo no vacío, `active` boolean y rol interno válido |
| Usuario no aparece | Comprobar vínculo backchannel, bindings de la aplicación/grupo y eventos del worker authentik |
| Cuenta eliminada al quitarla del grupo | Revisar el alcance de sincronización; restaurar solo desde el respaldo privado y corregir bindings antes de repetir |
| Inicio funciona pero mantenimiento devuelve 403 | Revisar `title`/`lab_role`, rol reconocido y rol efectivo local; no relajar controles del servidor |

Ante divergencia de datos, detén la sincronización. Conserva el volumen original y exporta un respaldo antes de corregir el scope. No uses `db reset`, truncados o reinicios destructivos.

## Referencias oficiales

- [authentik: precio y características Open Source](https://goauthentik.io/pricing/)
- [authentik: OIDC/OAuth2 y flujos](https://docs.goauthentik.io/add-secure-apps/providers/oauth2/)
- [authentik: crear provider OIDC](https://docs.goauthentik.io/add-secure-apps/providers/oauth2/create-oauth2-provider)
- [authentik: provider SCIM y token estático](https://docs.goauthentik.io/add-secure-apps/providers/scim/)
- [authentik: crear provider SCIM y configurarlo como backchannel](https://docs.goauthentik.io/add-secure-apps/providers/scim/create-scim-provider/)
- [authentik: instalación Docker Compose](https://docs.goauthentik.io/install-config/install/docker-compose/)
- [authentik: MFA TOTP](https://docs.goauthentik.io/add-secure-apps/flows-stages/stages/authenticator_totp/)
- [authentik: MFA WebAuthn](https://docs.goauthentik.io/add-secure-apps/flows-stages/stages/authenticator_webauthn/)
