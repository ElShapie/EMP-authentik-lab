# TI: servidor, red y Microsoft 365

## Archivos implementados

`preparar_runtime.py` copia aplicación, NVR y RFID a una carpeta externa y crea secretos locales. `red.py` comprueba un puerto TCP indicado. `Manage-LabUser.ps1` ofrece operaciones Microsoft Graph. La aplicación incluye Dockerfile y Compose; sus acciones guardan cambios en SQLite.

## 1. Preparar archivos sin datos en el repositorio

Desde la raíz, en Ubuntu:

```bash
python3 Areas/TI/preparar_runtime.py
```

Se crean `~/lab-runtime/app`, `nvr` y `rfid`. Los dos secretos de la aplicación se generan automáticamente y nunca se imprimen. Una ejecución posterior conserva `.env`; revisar cambios de ejemplos antes de una actualización. El programa rechaza como destino una carpeta dentro del repositorio.

Instalar Docker según [la guía TI](../../docs/Guias/03_TI.md). Completar `~/lab-runtime/app/.env` con IAM. APP_BASE_URL debe ser HTTPS; los campos OIDC deben pertenecer al tenant real. Si todavía no hay cámaras, dejar NVR_BASE_URL vacío.

## 2. Arrancar el servidor

```bash
cd ~/lab-runtime/app
sudo docker compose build
sudo docker compose up -d
curl http://127.0.0.1:8000/health
sudo docker compose logs --tail=100 app
```

Se publica únicamente en la propia laptop, puerto 8000. El volumen Docker app-data conserva usuarios y eventos. No ejecutar `docker compose down -v`: esa opción elimina el volumen y sus datos.

En otra terminal, iniciar el túnel de práctica:

```bash
sudo docker run --rm --network host cloudflare/cloudflared:latest tunnel --url http://127.0.0.1:8000
```

Actualizar APP_BASE_URL, el callback y la base SCIM con la dirección obtenida. Después de editar `.env`, recrear el contenedor:

```bash
cd ~/lab-runtime/app
sudo docker compose up -d --force-recreate
```

La alternativa Gunicorn con entorno virtual sigue disponible en la guía Python. Escoger una forma de arranque; no iniciar dos procesos en el mismo puerto.

## 3. Probar red y recurso

```bash
python3 Areas/TI/red.py --host 10.31.0.20 --puerto 8971
```

Ejecutar desde la raíz del repositorio y sustituir la IP de ejemplo. TCP disponible no certifica contraseña, video ni certificado. Con el ingeniero autenticado, `/consulta` devuelve modo y contador. `/mantenimiento` incrementa maintenance_runs y registra fecha; la cuenta administradora cambia mode a ready/maintenance. El auditor no debe poder modificarlos. Estas operaciones cambian el recurso de aplicación, no comandos del sistema operativo.

## 4. Microsoft Graph en PowerShell

En una laptop Windows o con PowerShell instalado, preparar módulos:

```powershell
Install-Module Microsoft.Graph.Authentication,Microsoft.Graph.Users,Microsoft.Graph.Users.Actions,Microsoft.Graph.Reports -Scope CurrentUser
```

Revisar el script antes de ejecutarlo. Usar un tenant autorizado y una cuenta administrativa con permisos adecuados. Sustituir REEMPLAZAR_TENANT y el correo por una cuenta de práctica del dominio verificado. `example.test` es ficticio y no permite crear cuentas Microsoft reales.

```powershell
./Areas/TI/Manage-LabUser.ps1 -Action Create -TenantId REEMPLAZAR_TENANT -UserPrincipalName ingeniero@example.test -Department TI
./Areas/TI/Manage-LabUser.ps1 -Action Update -TenantId REEMPLAZAR_TENANT -UserPrincipalName ingeniero@example.test -Department Auditoria
./Areas/TI/Manage-LabUser.ps1 -Action ResetPassword -TenantId REEMPLAZAR_TENANT -UserPrincipalName ingeniero@example.test
```

Create y ResetPassword solicitan contraseña por entrada protegida y exigen cambio al siguiente inicio. Graph debe cumplir la política del tenant; no se fuerza una política distinta desde este script. La cuenta y los roles administrativos son independientes de los roles de la aplicación.

Para licencia disponible, obtener SkuId desde la consola o Get-MgSubscribedSku con el módulo/permisos de esa consulta. Configurar UsageLocation real de dos letras y ejecutar AssignLicense. No comprar licencias automáticamente.

```powershell
./Areas/TI/Manage-LabUser.ps1 -Action AssignLicense -TenantId REEMPLAZAR_TENANT -UserPrincipalName ingeniero@example.test -UsageLocation REEMPLAZAR_PAIS -SkuId REEMPLAZAR_SKU
./Areas/TI/Manage-LabUser.ps1 -Action Audit -TenantId REEMPLAZAR_TENANT -UserPrincipalName ingeniero@example.test
./Areas/TI/Manage-LabUser.ps1 -Action Block -TenantId REEMPLAZAR_TENANT -UserPrincipalName ingeniero@example.test
```

Audit consulta inicios del usuario y los últimos eventos de auditoría del directorio; verificar qué cuenta afecta cada evento. Block deshabilita inicio y solicita revocación. Para eliminar una cuenta temporal, usar Delete con ConfirmLabDeletion y confirmar la cuenta solicitada; no eliminar el usuario principal antes del recorrido.

## 5. MFA, roles y amenazas

Seguir las pantallas de la guía TI para roles, valores predeterminados de seguridad o políticas autorizadas, registro del método y desafío MFA. Revisar Entra y Microsoft Defender según licencia. Documentar ausencia de alertas sin inventar incidentes. Este script no configura Acceso Condicional ni asigna privilegios administrativos. Las operaciones Graph no se han ejecutado contra un tenant desde este repositorio.

## Referencias

- [New-MgUser](https://learn.microsoft.com/en-us/powershell/module/microsoft.graph.users/new-mguser?view=graph-powershell-1.0).
- [Update-MgUser](https://learn.microsoft.com/en-us/powershell/module/microsoft.graph.users/update-mguser).
- [Set-MgUserLicense](https://learn.microsoft.com/en-us/powershell/module/microsoft.graph.users.actions/set-mguserlicense).
- [Revoke-MgUserSignInSession](https://learn.microsoft.com/en-us/powershell/module/microsoft.graph.users.actions/revoke-mgusersigninsession).
- [Get-MgAuditLogSignIn](https://learn.microsoft.com/en-us/powershell/module/microsoft.graph.reports/get-mgauditlogsignin).
- [Docker Compose Build](https://docs.docker.com/reference/compose-file/build/).
