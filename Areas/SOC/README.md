# SOC: hub y reconstrucción del recorrido

## Herramientas

`/hub` muestra los últimos 100 eventos de la aplicación y un enlace a Frigate. Los roles soc, auditor y admin pueden consultarlo. `exportar_eventos.py` genera JSON local desde SQLite; `linea_tiempo.py` relaciona RFID y aplicación por identidad explícita y UTC. authentik, Microsoft 365 y video mantienen sus fuentes originales; la correlación de estas fuentes sigue requiriendo revisión del operador.

## 1. Abrir el puesto SOC

1. IAM aprovisiona LAB-SOC con title soc y MFA.
2. TI configura NVR_BASE_URL con la URL HTTPS del NVR y recrea el servicio.
3. SOC inicia sesión en la aplicación y abre `/hub`.
4. Abre Frigate con una cuenta de consulta propia y las dos cámaras.
5. Verifica que una acción del ingeniero aparece en la tabla al actualizar.
6. Comprueba que el operador SOC no puede ejecutar administración ni mantenimiento.

El navegador del SOC necesita acceso a la red local del NVR. El túnel de la aplicación no publica las cámaras. El enlace conserva la protección del NVR y su certificado.

## 2. Exportar eventos

Si la aplicación usa Gunicorn y APP_DB relativo a su carpeta:

```bash
python3 Areas/SOC/exportar_eventos.py --base ~/lab-runtime/app/data/lab.sqlite --salida ~/lab-runtime/soc/eventos_aplicacion.json
```

Si utiliza Docker, TI copia la base con el contenedor detenido brevemente para una copia consistente:

```bash
cd ~/lab-runtime/app
sudo docker compose stop app
sudo docker compose cp app:/app/data/lab.sqlite ./copia_lab.sqlite
sudo docker compose start app
```

Después, desde la raíz del clon, exportar indicando `--base ~/lab-runtime/app/copia_lab.sqlite`. Si existe un archivo SQLite de journal/WAL por un método distinto de operación, obtener una copia consistente mediante respaldo SQLite o copiar sus archivos necesarios con el servicio detenido.

## 3. Obtener RFID

Seguridad Física detiene el registrador con Ctrl+C y entrega una copia del CSV. El identificador del ingeniero debe ser LAB-INGENIERO tanto en el programa de la placa como en externalId de la cuenta SCIM. No unir automáticamente un UUID desconocido con una persona por una hora similar.

## 4. Crear línea de tiempo

```bash
python3 Areas/SOC/linea_tiempo.py --rfid ~/lab-runtime/rfid/eventos_rfid.csv --aplicacion ~/lab-runtime/soc/eventos_aplicacion.json --empleado LAB-INGENIERO --salida ~/lab-runtime/soc/recorrido.html
```

Abrir el HTML local. Debe mostrar entrada, login, mantenimiento, cierre y salida cuando esos eventos realmente se hayan registrado. Los mensajes RFID tienen la hora de recepción en laptop. Las fechas requieren zona horaria y se convierten a UTC; un evento sin zona se rechaza. La página escapa texto para que no se ejecute HTML de un registro.

## 5. Revisar video y otras plataformas

Buscar el periodo en Frigate y confirmar cruce físico, no únicamente una tarjeta leída. Relacionar MFA/provisioning en authentik y cuentas/licencias en Microsoft 365 por identidad y periodo. Guardar incidentes usando Plantillas/incidentes.csv en una carpeta externa. Para rechazo digital, guardar el 403 y que el contador/estado no cambió. Para fallo de cámara, registrar intervalo sin video, recuperación y grabación nueva.

## Entrega

Vista del hub, línea de tiempo, video exportado del recorrido, registro de incidentes y relación de fuentes. Guardar todo fuera de GitHub, incluso siendo un repositorio privado. Completar las verificaciones de [la guía SOC](../../docs/Guias/05_SOC.md).
