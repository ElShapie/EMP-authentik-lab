# Dirección: ejecutar y coordinar la práctica

## Herramientas entregadas

`control.py` mantiene un plan local con 31 puestos, actividades por departamento y estados de avance. `plan.example.json` contiene puestos genéricos y tareas, sin asignaciones personales. La documentación completa del área está en `docs/Guias/01_Direccion.pdf`.

## 1. Descargar y preparar

La persona propietaria debe agregar las cuentas GitHub autorizadas desde Settings → Collaborators. Cada colaborador acepta la invitación. Leer un repositorio privado requiere acceso; compartir su dirección por sí solo no lo concede.

```bash
git clone https://github.com/ElShapie/EMP-authentik-lab.git
cd EMP-authentik-lab
python3 Areas/Direccion/control.py iniciar
python3 Areas/Direccion/control.py ver
```

El plan se guarda en `~/lab-runtime/direccion/plan.json`. Una segunda ejecución de iniciar se detiene para conservar lo que ya registraron. Asignar personas en el control privado y utilizar los códigos de puesto para compartir instrucciones.

## 2. Definir responsables y recursos

1. Revisar los 31 puestos: Dirección 3, RRHH 3, TI 7, IAM 5, SOC 5, Seguridad Física 5 y Auditoría 3.
2. Designar dos laptops por área. Mantener servidor TI y grabador encendidos durante el ensayo.
3. Confirmar router, uno o dos switches, cables, carga de teléfonos y espacio de almacenamiento.
4. Registrar el modelo exacto de lector y placa. No autorizar cableado mientras estén sin identificar.
5. Confirmar con el profesor cuál proveedor de identidad está aprobado para esta entrega. `main` exige OneLogin; esta rama usa authentik con autorización expresa. Confirmar OIDC/aprovisionamiento y Microsoft 365.
6. Acordar por escrito cómo se cubre el requisito de transceptores de video con las cámaras IP y el NVR virtual autorizado.

## 3. Registrar avances

```bash
python3 Areas/Direccion/control.py actualizar --tarea TI-01 --estado en_proceso --responsable PUESTO-008
python3 Areas/Direccion/control.py actualizar --tarea TI-01 --estado validado --responsable PUESTO-008 --evidencia EVIDENCIA-RED-01
```

La primera orden indica trabajo iniciado. La segunda necesita una referencia local de evidencia. El programa no determina por sí mismo que el resultado sea verdadero: Dirección revisa la prueba con Auditoría. Estados disponibles: pendiente, en_proceso, implementado, validado y bloqueado.

## 4. Orden del montaje

1. RRHH registra solicitudes; TI prepara la red y el servidor.
2. Seguridad Física prepara RFID, teléfonos y Frigate.
3. IAM configura OIDC + SCIM 2.0 en authentik (solo si el profesor aprobó esta variante) y demuestra altas/bajas.
4. TI completa los ejercicios Microsoft 365.
5. SOC consulta `/hub` con su rol y genera la línea de tiempo.
6. Auditoría corre pruebas locales y luego el recorrido real.
7. Cada área entrega sus archivos de evidencia a una carpeta privada y registra su referencia en el plan.

## 5. Recorrido de exposición

RRHH muestra la solicitud aprobada del ingeniero. Un visitante presenta una tarjeta y recibe rechazo. El ingeniero presenta su tarjeta permitida; el operador marca entrada. El ingeniero inicia con el proveedor aprobado y MFA, consulta el estado y ejecuta mantenimiento. Un auditor inicia y prueba la misma acción: debe recibir 403 sin modificar el recurso. El ingeniero cierra sesión y el operador registra salida. SOC relaciona los eventos con el video. Al final, IAM cambia el rol y luego suspende la cuenta; repetir la acción desde una sesión anterior demuestra retiro de permisos.

## Resultado y entrega

Plan actualizado, responsables definidos en privado, recursos confirmados y recorrido ensayado. No presentar una grabación configurada como si ya existieran 24 horas de video. `Entrega/` contiene bases de informe y presentación que deben completarse con resultados reales. Consultar [referencias](../../docs/REFERENCIAS_Y_VIDEOS.md).
