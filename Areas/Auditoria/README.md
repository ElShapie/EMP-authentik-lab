# Auditoría: comprobar implementación y preparar entrega

## Herramientas

`pruebas_locales.py` ejecuta tres suites y puede guardar un resumen local. `evidencias.py` genera un manifiesto SHA-256 de archivos existentes. `Entrega/` contiene un informe inglés en LaTeX IEEE y una presentación base. Las herramientas no declaran aprobadas pruebas de hardware o nube que todavía no se ejecutaron.

## 1. Preparar Python

Desde la raíz, en Ubuntu:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r Implementacion/app/requirements.txt -r scripts/requirements-check.txt
python Areas/Auditoria/pruebas_locales.py --salida ~/lab-runtime/auditoria/pruebas_locales.json
python scripts/check_public_content.py
```

Las pruebas locales comprueban almacenamiento, permiso, cambio/baja con sesión anterior, CSRF, respuestas SCIM, rechazo de JSON mal formado, hub SOC, aprobaciones RRHH, orden de eventos y cambios de hashes. Las respuestas OIDC se sustituyen exclusivamente en los tests de vínculo de identidad; firma/token/MFA se comprueban contra authentik en el ensayo real.

## 2. Pruebas de integración

1. Verificar alta enviada desde authentik y cuenta creada sin alta manual local.
2. Verificar el desafío MFA con una sesión nueva.
3. Con ingeniero, leer estado, ejecutar mantenimiento y comprobar incremento persistente.
4. Con auditor y SOC, intentar modificar estado/mantenimiento y comprobar 403 sin cambio.
5. Cambiar rol y repetir desde la sesión anterior.
6. Suspender/eliminar por SCIM y repetir sesión anterior e inicio nuevo.
7. Comprobar cuatro tarjetas permitidas y una desconocida rechazada.
8. Relacionar entrada/salida con el video, CSV y registros de aplicación.
9. Comprobar video sin movimiento, móvil, recuperación y duración real de continuidad.
10. Comprobar alta, cambio, contraseña, licencia, rol, MFA, auditoría y baja de Microsoft 365 según recursos disponibles.

Para cada caso registrar condición inicial, pasos, resultado esperado, resultado observado, hora, responsable y referencia de evidencia. Un recurso sin licencia es una limitación, no una prueba aprobada. Copiar Plantillas/pruebas.csv a una carpeta privada y completar allí.

## 3. Manifestar archivos reales

```bash
python Areas/Auditoria/evidencias.py --carpeta ~/lab-runtime/evidencias --salida ~/lab-runtime/auditoria/manifiesto.json
```

El comando calcula tamaño y SHA-256 de cada archivo y omite la propia salida si está dentro de la carpeta. Un hash permite comprobar cambios posteriores; no prueba que un video represente una acción aprobada. Mantener evidencia, manifestación y claves fuera del repositorio.

## 4. Informe inglés

Leer `Entrega/informe_IEEE.tex` y su PDF base. Reemplazar las secciones de resultados pendientes por hechos comprobados: qué cuenta, acción y periodo se usaron, sin divulgar identificadores personales. Añadir limitaciones de hardware, licencias y grabación. Para la copia final requerida por la evaluación, completar autores en privado; el repositorio conserva el ejemplo sin personas ni institución.

Compilar con XeLaTeX, Times New Roman y clase IEEEtran. Revisar dos columnas, tablas, citas y fuentes. Las referencias del informe se enlazan a documentación oficial. El informe base describe diseño e implementación y distingue las 36 pruebas locales de las pruebas de integración pendientes.

## 5. Presentación y cierre

Actualizar la presentación con evidencias sanitizadas, resultados y limitaciones del ensayo. Mantener los diagramas aparte para insertar solo los necesarios. Ensayar con Dirección el recorrido y las transiciones de cuentas. Conservar copias locales y cerrar cuentas temporales al finalizar según autorización del tenant.

## Entrega

Lista completa de pruebas, resultados reales, manifiesto, informe en inglés, presentación y relación de aportaciones del grupo guardada privadamente. [Guía de Auditoría](../../docs/Guias/07_Auditoria.md).
