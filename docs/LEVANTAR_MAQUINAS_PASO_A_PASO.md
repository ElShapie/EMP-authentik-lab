# Levantar las máquinas virtuales y los servidores operativos

Esta guía construye el entorno desde cero. Los ejemplos usan una red privada `10.31.0.0/24` y Ubuntu Server 24.04 LTS. Cambia las direcciones si chocan con la red del salón. No uses nombres, correos, tarjetas ni contraseñas reales en capturas o commits.

## 1. Resultado esperado

Al terminar habrá cuatro máquinas separadas:

| Nombre | IP de ejemplo | Recursos | Función |
|---|---|---:|---|
| `VM-HUB-01` | `10.31.0.20` | 2 vCPU, 4 GB RAM, 40 GB | Aplicación, SQLite, receptor SCIM, RFID, inventario y SOC |
| `VM-IAM-01` | `10.31.0.23` | Por dimensionar mediante prueba | authentik Open Source y PostgreSQL persistente |
| `VM-NVR-01` | `10.31.0.21` | 4 vCPU, 8 GB RAM, 120 GB | Frigate y grabaciones |
| `VM-RESPALDO-01` | `10.31.0.22` | 2 vCPU, 2 GB RAM, 80 GB | Copias y restauraciones de prueba |

Los teléfonos usan direcciones reservadas, por ejemplo `10.31.0.31` y `10.31.0.32`. La interfaz se abre como `https://security-hub.lab`; authentik usa un DNS HTTPS independiente definido por TI. El dashboard DPO no se instala en estas VM ni comparte su base de datos.

## 2. Preparar el hipervisor

Puede utilizarse VirtualBox, VMware, Hyper-V o Proxmox. En cada VM:

1. Crea una VM nueva con Ubuntu Server 24.04 LTS de 64 bits.
2. Asigna los recursos de la tabla anterior.
3. Usa un disco dinámico. Para el NVR, coloca el disco de video en una unidad con suficiente espacio.
4. Conecta la interfaz de red a un puente o red externa para que las laptops y teléfonos puedan alcanzar la VM.
5. Desactiva carpetas compartidas y portapapeles bidireccional si no son necesarios.
6. Instala Ubuntu con OpenSSH Server y sin entorno gráfico.
7. Crea una cuenta administrativa de laboratorio que no contenga el nombre de una persona.
8. Después de actualizar Ubuntu, crea una instantánea llamada `base-actualizada`.

Si el hipervisor está en una laptop, configura esa laptop para no suspenderse durante la práctica.

## 3. Configurar red y nombre

En cada VM identifica la interfaz:

```bash
ip -br link
ip route
```

Configura una reserva DHCP en el router si es posible. Si se requiere una IP fija, edita el archivo de Netplan que ya exista en `/etc/netplan/`; no inventes el nombre de la interfaz. Ejemplo para `VM-HUB-01`:

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: false
      addresses: [10.31.0.20/24]
      routes:
        - to: default
          via: 10.31.0.1
      nameservers:
        addresses: [10.31.0.1, 1.1.1.1]
```

Comprueba la sintaxis antes de aplicar:

```bash
sudo netplan try
sudo netplan apply
ping -c 3 10.31.0.1
ping -c 3 DOMINIO_AUTHENTIK
```

Asigna el nombre correcto en cada VM:

```bash
sudo hostnamectl set-hostname VM-HUB-01
```

Repite con `VM-IAM-01`, `VM-NVR-01` y `VM-RESPALDO-01`.

## 4. Actualizar y proteger Ubuntu

Ejecuta en las cuatro VM:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y ca-certificates curl git ufw unattended-upgrades
sudo timedatectl set-timezone UTC
sudo systemctl enable --now systemd-timesyncd
timedatectl status
```

Habilita SSH solo desde la red del laboratorio y después el firewall:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.31.0.0/24 to any port 22 proto tcp
sudo ufw enable
sudo ufw status verbose
```

No desactives el firewall hasta haber confirmado que la regla SSH coincide con la red real.

## 5. Instalar Docker

En `VM-HUB-01`, `VM-IAM-01` y `VM-NVR-01`:

```bash
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Cierra la sesión SSH y entra de nuevo. Verifica:

```bash
docker version
docker compose version
docker run --rm hello-world
```

## 6. Instalar el Security Hub

En `VM-HUB-01`, clona el repositorio privado utilizando una credencial de GitHub de alcance mínimo:

```bash
git clone https://github.com/ElShapie/EMP-authentik-lab.git
cd EMP-authentik-lab
python3 Areas/TI/preparar_runtime.py --destino "$HOME/lab-runtime"
cd "$HOME/lab-runtime/app"
chmod 600 .env
```

El preparador genera cuatro secretos diferentes: sesión, SCIM, dispositivos y protección de tarjetas. Abre `.env` y completa los datos de la instancia authentik que preparará IAM:

```bash
nano .env
```

Valores que deben coincidir:

```text
HUB_HOST=security-hub.lab
APP_BASE_URL=https://security-hub.lab
OIDC_PROVIDER_NAME=authentik
OIDC_CLIENT_ID=valor generado para la aplicación OIDC
OIDC_CLIENT_SECRET=valor generado para la aplicación OIDC
OIDC_METADATA_URL=https://authentik.example.test/application/o/security-hub/.well-known/openid-configuration
NVR_BASE_URL=https://nvr.lab:8971
```

No muestres el archivo con `cat` durante una grabación y no lo copies al repositorio.

La rama `main` de `EMP-authentik-lab` contiene la variante authentik. El repositorio fuente conserva OneLogin y no debe usarse para levantar esta variante.

## 7. Configurar authentik

Sigue primero [la guía detallada de IAM/authentik](Guias/04_IAM_Authentik.md). En la aplicación OIDC registra:

```text
Login URL:    https://security-hub.lab/login
Redirect URI: https://security-hub.lab/auth/callback
Issuer:       el valor publicado en el documento OIDC de authentik
```

Después configura el proveedor SCIM en authentik con:

```text
Base URL:     https://security-hub.lab/scim/v2
Bearer token: valor SCIM_TOKEN del .env
```

Mapea estos atributos:

| authentik | SCIM/Hub | Ejemplo ficticio |
|---|---|---|
| Correo | `userName` | `puesto01@example.test` |
| Número de empleado | `externalId` | `LAB-001` |
| Rol inicial | `title` | `consulta` |
| Estado | `active` | `true` |

El número EMP debe ser único. `lab_role` proporciona el rol inicial; después TI puede establecer un rol efectivo desde la interfaz del Hub. Desactivar o retirar la asignación al usuario en authentik debe provocar la baja SCIM y bloquear su acceso.

## 8. Iniciar HTTPS y el Hub

El `compose.yml` levanta la aplicación y Caddy. Caddy genera una autoridad local para `security-hub.lab`.

```bash
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 app
docker compose logs --tail=100 caddy
```

Abre los puertos del Hub solo en la red local:

```bash
sudo ufw allow from 10.31.0.0/24 to any port 80 proto tcp
sudo ufw allow from 10.31.0.0/24 to any port 443 proto tcp
```

Extrae el certificado raíz local:

```bash
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./security-hub-root.crt
```

Distribuye ese certificado por un canal controlado e instálalo únicamente en los equipos del laboratorio. En Ubuntu:

```bash
sudo cp security-hub-root.crt /usr/local/share/ca-certificates/security-hub-root.crt
sudo update-ca-certificates
```

En cada laptop añade temporalmente la resolución local, o configura el DNS del laboratorio:

```text
10.31.0.20 security-hub.lab
10.31.0.23 authentik.lab
10.31.0.21 nvr.lab
```

En Windows ese archivo es `C:\Windows\System32\drivers\etc\hosts` y requiere permisos de administrador. Instala el certificado en “Entidades de certificación raíz de confianza” solamente para la práctica. Retíralo al terminar si ya no se utilizará.

Comprueba desde una laptop:

```bash
curl https://security-hub.lab/health
```

Debe devolver `{"status":"ok"}` sin advertencias TLS. Después prueba el inicio con authentik y la guía [IAM/authentik](Guias/04_IAM_Authentik.md).

## 9. Levantar el NVR

En `VM-NVR-01`:

```bash
git clone https://github.com/ElShapie/EMP-authentik-lab.git
cd EMP-authentik-lab
python3 Areas/TI/preparar_runtime.py --destino "$HOME/lab-runtime"
cd "$HOME/lab-runtime/nvr"
mkdir -p config media certs
cp config.example.yml config/config.yml
chmod 600 .env
nano .env
nano config/config.yml
```

Configura las IP reservadas de los teléfonos y sus credenciales locales. No uses la contraseña personal del propietario del teléfono. Inicia Frigate:

```bash
docker compose config
docker compose up -d
docker compose ps
docker compose logs --tail=100 frigate
```

Autoriza sus puertos únicamente desde la red del laboratorio y desde `VM-HUB-01`. Comprueba primero una cámara a 640×480 y 5 FPS. Agrega la segunda después de verificar CPU, RAM y espacio:

```bash
docker stats --no-stream
df -h
```

## 10. Preparar el respaldo

En `VM-RESPALDO-01` crea un usuario sin acceso interactivo compartido y una carpeta cifrada o un volumen cifrado. El respaldo mínimo contiene el volumen `app-data` y la configuración privada necesaria para una restauración. Las grabaciones del NVR se respaldan solo si el guion de la práctica lo exige.

Detén escrituras durante una copia coherente:

```bash
cd "$HOME/lab-runtime/app"
docker compose stop app
docker run --rm -v app_app-data:/source:ro -v "$PWD/backups:/backup" alpine \
  tar -czf /backup/hub-data.tar.gz -C /source .
docker compose start app
sha256sum backups/hub-data.tar.gz
```

El nombre real del volumen puede variar. Confírmalo con `docker volume ls`; no adivines ni borres volúmenes. Cifra el archivo antes de transferirlo y prueba una restauración en una VM de ensayo.

## 11. Prueba integral

Ejecuta en este orden:

1. authentik aprovisiona dos identidades ficticias con identificadores EMP distintos.
2. TI inicia sesión y asigna roles desde “Personas y tarjetas”.
3. Seguridad Física registra una tarjeta ficticia para uno de esos empleados.
4. El lector consulta `/api/v1/access/check` y recibe `allowed: true`.
5. Se bloquea la tarjeta desde la interfaz; la siguiente consulta devuelve `allowed: false`.
6. SOC observa ambos eventos y abre un incidente de prueba.
7. TI marca el NVR en mantenimiento y después disponible.
8. Auditoría comprueba que los cambios de rol y tarjeta aparecen en los eventos.
9. Se crea un respaldo y se valida su SHA-256.

No se considera terminado hasta que otro integrante pueda repetir la prueba usando únicamente estas guías.

## 12. Apagado ordenado

Al finalizar:

```bash
cd "$HOME/lab-runtime/app"
docker compose stop
```

En el NVR:

```bash
cd "$HOME/lab-runtime/nvr"
docker compose stop
```

Después apaga Ubuntu con `sudo poweroff`. No apagues la VM desde el hipervisor mientras SQLite o Frigate están escribiendo.
