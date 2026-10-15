# Identity Access Practice — variante authentik

Esta rama prepara una alternativa técnica con authentik Open Source. **No cambia `main`**, que conserva el requisito original de OneLogin. La guía original del proyecto declara OneLogin obligatorio; usa esta variante para la entrega únicamente después de obtener autorización del profesor. No conectes esta rama al volumen de datos del despliegue OneLogin.

Repositorio privado de implementación de un laboratorio con 31 puestos. El contenido usa identificadores genéricos; los nombres, cuentas, tarjetas, grabaciones y evidencias se guardan fuera del repositorio.

## Organización y guías

| Departamento | Puestos | Guía y herramientas |
|---|---:|---|
| Dirección | 3 | [Plan de trabajo y seguimiento](Areas/Direccion/README.md) |
| RRHH | 3 | [Solicitudes, aprobación y cierre](Areas/RRHH/README.md) |
| TI | 7 | [Red, aplicación, Docker y Microsoft 365](Areas/TI/README.md) |
| IAM | 5 | [authentik, MFA, roles y SCIM 2.0](Areas/IAM/README.md) |
| SOC | 5 | [Eventos, monitoreo y línea de tiempo](Areas/SOC/README.md) |
| Seguridad física | 5 | [RFID, cámaras de teléfonos y Frigate](Areas/Seguridad_Fisica/README.md) |
| Auditoría | 3 | [Pruebas, evidencias y entrega](Areas/Auditoria/README.md) |

Cada área tiene una guía Markdown y su versión PDF/LaTeX, con comandos, orden de trabajo, resultados esperados y referencias. Las guías generales y videos están en [docs](docs/LEER_PRIMERO.md). Los [diagramas](docs/Diagramas) están separados de las guías. Las [plantillas](Plantillas) contienen únicamente encabezados.

## Comenzar

Se necesita acceso como colaborador para clonar este repositorio privado.

```bash
git clone https://github.com/ElShapie/identity-access-practice.git
cd identity-access-practice
python3 Areas/TI/preparar_runtime.py
```

El preparador copia los componentes a `~/lab-runtime` y genera secretos únicamente en esa carpeta. Completar la configuración siguiendo TI e IAM antes de iniciar servicios. No subir esa carpeta a GitHub.

## Componentes implementados

- Aplicación Flask con inicio de sesión OIDC configurable (authentik en esta rama), permisos por rol y revisión del usuario activo en cada operación. Una sesión anterior pierde acceso cuando se desactiva o elimina su usuario local.
- El Security Hub, sus servidores virtuales, NVR, RFID, documentación y diagramas de VLAN se mantienen en el repositorio privado separado [security-hub-infrastructure](https://github.com/ElShapie/security-hub-infrastructure). Las copias presentes en este historial se conservan únicamente como referencia de la entrega original.
- SCIM 2.0 para altas, cambios y bajas desde authentik; la integración externa debe configurarse y probarse con la instancia real.
- Recurso de práctica persistente: consultar estado, ejecutar mantenimiento e incrementar su contador, cambiar modo desde Administración, revisar eventos y abrir el enlace al NVR desde el hub. Estas operaciones modifican la aplicación; no administran el sistema operativo.
- RRHH registra solicitudes y exige aprobación por un actor distinto y el área correspondiente. Los identificadores de actor del CLI no constituyen autenticación.
- TI incluye preparador de configuración, comprobación TCP y comandos PowerShell para Microsoft 365.
- SOC exporta eventos y construye una línea de tiempo por identificador y hora UTC. La correlación con video se realiza siguiendo la guía.
- Seguridad física incluye código condicional para Arduino Uno/MFRC522 y configuración ejemplo de Frigate. Confirmar el hardware antes de usar ese código.
- Auditoría ejecuta pruebas reales del código local y genera inventarios SHA-256 de evidencias privadas.

## Verificar antes de integrar

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r Implementacion/app/requirements.txt -r scripts/requirements-check.txt
python Areas/Auditoria/pruebas_locales.py
python scripts/check_public_content.py
```

Las pruebas locales cubren almacenamiento, permisos, control de publicación, endpoints HTTP y herramientas operativas. Los casos de identidad usan respuestas simuladas únicamente en pruebas; no certifican la instancia authentik ni Microsoft 365. GitHub Actions repite pruebas, comprueba sintaxis PowerShell y construye la imagen de la aplicación.

## Orden de integración

1. Dirección asigna los 31 puestos y registra responsables en un control privado.
2. TI prepara la red y las laptops designadas, copia los componentes y completa configuración.
3. IAM configura authentik, MFA, grupos, aplicación OIDC y aprovisionamiento SCIM 2.0.
4. RRHH emite solicitudes; TI e IAM implementan y verifican el ciclo de identidades.
5. Seguridad física confirma lector, registra exactamente cuatro identidades autorizadas y conecta teléfonos a Frigate.
6. SOC comprueba cámaras, grabación continua, eventos y correlación del escenario.
7. Auditoría ejecuta las pruebas integradas, recoge evidencias y completa el informe con resultados medidos.

## Entregables

[Informe IEEE en inglés](Entrega/informe_IEEE.pdf), su [fuente LaTeX](Entrega/informe_IEEE.tex) y [presentación editable](Entrega/Presentacion_practica.pptx). El informe distingue resultados locales de pruebas pendientes; debe completarse tras ejecutar el escenario físico y los servicios externos. PDFs en blanco y negro con Times New Roman. Para recompilar, instalar XeLaTeX y la fuente solicitada y ejecutar `python scripts/compile_docs.py`.

## Alcance pendiente

La instancia real de authentik, las cuentas y licencias de Microsoft 365, el modelo RFID, la conexión de cámaras y la prueba continua de 24 horas requieren ejecución por el equipo. La integración OIDC/SCIM está implementada localmente; el tenant, MFA y ciclo real de altas/bajas siguen pendientes de validar. La instalación Docker de la aplicación se documenta y su imagen se comprueba en CI; no se ha desplegado en las laptops del salón.

Seguir [PRIVACIDAD.md](PRIVACIDAD.md) y [CONTRIBUTING.md](CONTRIBUTING.md). La privacidad del repositorio no autoriza guardar secretos ni datos personales. Invitar integrantes desde Settings → Collaborators; no compartir contraseñas.

## Guías actuales por identificador

Las [diligencias operativas](docs/DILIGENCIAS_POR_AREA.md) y los [cuadernos PDF por área](docs/Controles_Area/) usan identificadores `EMP` y no publican nombres personales. Cada responsable y trabajador puede consultar actividad, entregable, pruebas y ruta de reporte.
