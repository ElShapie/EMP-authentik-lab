# Seguridad Física: RFID, cámaras y NVR

## Implementación entregada

El programa `Implementacion/rfid/control_acceso.ino` decide permiso para cuatro UID y controla LED. `registrar_tarjetas.py` guarda entradas/salidas con UTC y hora local. `Implementacion/nvr/` contiene Compose y configuración Frigate 0.17.1 para MJPEG Android y RTSP iPhone. El cableado está documentado para Uno/MFRC522; debe coincidir con el equipo disponible.

## 1. Confirmar hardware y leer UID

1. Identificar lector, placa, voltaje y tipo de conexión.
2. Si son Uno/MFRC522, seguir el cableado y adaptación eléctrica de la guía completa. MFRC522 requiere 3.3 V y no recibe directamente señales de 5 V sin adaptación adecuada.
3. Instalar Arduino IDE y biblioteca MFRC522.
4. Cargar el sketch con las cuatro entradas PENDIENTE: las tarjetas se rechazan, pero la salida muestra su UID.
5. Anotar los cuatro UID reales en privado y reemplazar los marcadores de LAB-INGENIERO, LAB-ADMIN, LAB-GUARDIA y LAB-AUDITOR.
6. Volver a cargar y comprobar cuatro permisos y un rechazo de tarjeta ajena.

Los UID se quedan en la copia de trabajo dentro de `~/lab-runtime/rfid/`; no modificar el ejemplo versionado con tarjetas reales. Si el hardware es otro, adaptar el código según su hoja de datos y repetir pruebas antes de la práctica.

## 2. Guardar entradas y salidas

Cerrar el monitor serie de Arduino IDE. Desde la copia runtime Ubuntu:

```bash
cd ~/lab-runtime/rfid
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pyserial
python -m serial.tools.list_ports -v
python registrar_tarjetas.py --puerto /dev/ttyACM0 --archivo eventos_rfid.csv
```

Reemplazar el puerto real. Escribir E y Enter para entrada; S y Enter para salida. La dirección la selecciona el operador. No inferir salida por la segunda lectura de una tarjeta. Comprobar movimiento, identidad, resultado y hora en el CSV. Para Windows seguir la guía Python con COM real.

## 3. Configurar teléfonos

Android: IP Webcam, resolución inicial 640x480 y 5 fps, autenticación propia y ruta MJPEG `/video`. iPhone: IP Camera Lite, servidor RTSP/H.264 y ruta que realmente muestre la aplicación. Probar cada stream en VLC/ffprobe antes de Frigate. Las direcciones y credenciales son locales; no incluirlas en capturas.

## 4. Preparar Frigate

TI copia los archivos con preparar_runtime. En el NVR:

```bash
cd ~/lab-runtime/nvr
mkdir -p config media certs
cp config.example.yml config/config.yml
chmod 600 .env
```

Editar `.env` con credenciales de las cámaras y `config/config.yml` con IP/rutas reales. Editar la dirección de escucha de Compose: 10.31.0.20 es un ejemplo. Usar certificado de laboratorio y distribuir su autoridad a los clientes según la guía Seguridad Física; no compartir la clave privada. Mantener puerto 8971 autenticado y no exponer 5000.

```bash
sudo docker compose config --quiet
sudo docker compose pull
sudo docker compose up -d
sudo docker compose logs --tail=100 frigate
```

Obtener la contraseña administrativa inicial del registro de primer inicio, cambiarla y crear cuentas de consulta. Esos logs y credenciales permanecen privados. Comprobar Live, reproducción, exportación y consulta móvil en la misma red.

## 5. Continuidad

Grabar un periodo con movimiento y otro sin movimiento: ambos deben existir. Reiniciar el servicio y comprobar grabaciones anteriores y nuevas. Para demostrar 24/7, conservar una prueba real de al menos 24 horas con cargadores, disco disponible y suspensión desactivada; la configuración continuous.days 1 por sí sola no demuestra que funcionó ese tiempo. SOC registra fallos e intervalos sin cobertura.

## Entrega

Esquema del cableado real, código adaptado conservado localmente, resultados de cinco tarjetas, CSV, configuración efectiva privada, video del recorrido y prueba de recuperación. Consultar [guía y videos](../../docs/Guias/06_Seguridad_Fisica.md).
