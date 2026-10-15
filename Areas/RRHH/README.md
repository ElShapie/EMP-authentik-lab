# RRHH: solicitudes, aprobaciones y cierre

## Qué implementa el programa

`solicitudes.py` crea un registro local en SQLite. Cada solicitud tiene tipo, recurso, identidad, rol, estado e historial. Impide que el solicitante se apruebe a sí mismo y exige un operador del área dueña. Para cerrar una solicitud se requiere aprobación y referencia de evidencia.

Es una herramienta administrativa local. Los argumentos actor y área no autentican a quien la ejecuta. RRHH opera la laptop designada; verifica la aprobación mediante el procedimiento del grupo. La identidad y los permisos de la aplicación se comprueban con authentik en esta rama. El programa no crea cuentas en los tenants ni cambia tarjetas.

## 1. Crear una solicitud por recurso

Desde la raíz del repositorio:

```bash
python3 Areas/RRHH/solicitudes.py crear --actor PUESTO-004 --empleado LAB-INGENIERO --tipo alta --recurso aplicacion --rol mantenimiento
```

Anotar el ID `SOL-...` que devuelve. La base predeterminada está en `~/lab-runtime/rrhh/control.sqlite`. El ID es generado en cada ejecución: copiar el real en los siguientes pasos.

Tipos: alta, cambio y baja. Recursos y dueños: aplicacion/TI, authentik/IAM, microsoft365/TI y rfid/Seguridad_Fisica. Una solicitud para varios sistemas se divide en solicitudes por recurso para comprobar cada ejecución.

## 2. Aprobar con el dueño

```bash
python3 Areas/RRHH/solicitudes.py aprobar --id REEMPLAZAR_SOL --actor PUESTO-008 --area TI
```

El solicitante del ejemplo es PUESTO-004; PUESTO-008 representa al revisor TI. Si actor coincide, área es incorrecta o ya fue aprobada, el programa devuelve error y conserva el estado. Guardar la aprobación real en el expediente privado.

## 3. Solicitar implementación

Entregar el ID y los datos al área responsable. IAM crea el usuario authentik, configura el rol y permite que SCIM cree la cuenta local. TI administra Microsoft 365 según su guía. Seguridad Física agrega o retira el UID en el código de la placa y lo vuelve a cargar. RRHH verifica cada resultado; una cuenta Microsoft 365 no implica que authentik o RFID estén configurados.

## 4. Cerrar con evidencia

```bash
python3 Areas/RRHH/solicitudes.py cerrar --id REEMPLAZAR_SOL --actor PUESTO-011 --evidencia EVIDENCIA-ALTA-01
python3 Areas/RRHH/solicitudes.py listar
```

La evidencia es una referencia privada, no la contraseña o el contenido del archivo. Estado implementada significa que el operador registró el cierre; Auditoría comprueba que la acción funciona.

## 5. Cambio de puesto

Crear tipo cambio para la misma identidad y nuevo rol auditor. Obtener aprobación, pedir a IAM cambiar el atributo y comprobar sincronización. Mantener una sesión anterior abierta: mantenimiento debe dejar de funcionar. TI revisa por separado Microsoft 365 y Seguridad Física revisa si corresponde retirar la tarjeta.

## 6. Baja

Crear tipo baja por recurso. IAM suspende o retira la cuenta y confirma SCIM. TI bloquea inicio y revoca sesiones Microsoft 365. Seguridad Física retira el UID. Probar una sesión anterior y la tarjeta; documentar tiempos efectivos. Cerrar cada solicitud después de la prueba correspondiente.

## Archivos y entrega

Mantener nombres, correos, aprobaciones, base de datos e historial fuera del clon. Utilizar las plantillas vacías de `Plantillas/` como punto de partida si necesitan Excel. Entregar a Auditoría las solicitudes y referencias en una carpeta privada. Más pasos: [guía RRHH](../../docs/Guias/02_RRHH.md).
