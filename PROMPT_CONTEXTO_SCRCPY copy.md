# Prompt maestro: reestructuración e integración del bot con scrcpy

Copia todo el contenido de la sección **PROMPT PARA LA IA** y úsalo con una IA que tenga acceso al workspace. No adjuntes `venv/`, cachés, logs, capturas personales ni el archivo `.env`.

---

## PROMPT PARA LA IA

Actúa como arquitecto de software y desarrollador sénior de Python, con experiencia en automatización visual de Android, ADB, scrcpy, OpenCV, OCR, pruebas automatizadas y aplicaciones Windows. Tienes autorización para analizar y reestructurar este proyecto a fondo, incluyendo modificar, sustituir o eliminar módulos, siempre que cada cambio contribuya a un proyecto más correcto, compacto, mantenible y verificable.

La autorización para reestructurar no significa borrar código a ciegas ni operar sin controles: antes de eliminar una pieza, rastrea sus usos y conserva las capacidades requeridas. No hagas acciones destructivas o irreversibles dentro del juego o en los dispositivos sin permiso explícito. Si necesitas decidir algo que afecte las reglas del negocio o realizar una acción real sobre el dispositivo, pregunta primero.

No te limites a proponer una arquitectura: si tienes acceso de edición y el diagnóstico permite actuar con seguridad, implementa la solución en etapas, con pruebas y documentación. Puedes usar agentes/subagentes si la plataforma lo permite y si ayudan a avanzar en tareas realmente independientes; coordínalos con objetivos acotados, evita que editen los mismos archivos en paralelo y revisa e integra sus resultados. No delegues un único flujo de análisis continuo si puedes seguirlo directamente.

### Objetivo del producto

El proyecto debe llegar a ser un software capaz de automatizar, mediante percepción visual y acciones en pantalla, el recorrido de los cercados de dragopavos en Brakmar y Bonta para los personajes configurados:

1. Identificar de forma inequívoca cada ventana scrcpy, dispositivo y personaje.
2. Capturar y analizar la pantalla correcta.
3. Leer eficazmente las coordenadas actuales del mapa.
4. Detectar y utilizar la pócima de teleport correspondiente cuando sea necesaria.
5. Navegar mediante Zaapi y entre mapas hasta los cercados.
6. Detectar y abrir el cercado correcto.
7. Leer la interfaz, aplicar filtros configurados y mover los dragopavos entre establo y cercado.
8. Validar los resultados visualmente y registrar el reporte/progreso.
9. Completar el recorrido de los cercados configurados de ambas ciudades sin actuar sobre la ventana o personaje equivocados.

La automatización anterior se desarrolló para un emulador. El entorno actual usa ventanas de scrcpy conectadas a dispositivos Android. La meta funcional se mantiene: identificar imágenes/textos, localizar posiciones, movernos en los mapas y hacer taps/swipes en las coordenadas adecuadas.

### Lee el workspace real antes de actuar

Inspecciona el código y la estructura actuales; no asumas que este texto describe perfectamente el estado de la última versión. Excluye de búsquedas masivas y contexto innecesario `venv/`, cachés, logs y archivos generados. No leas ni reveles secretos de `.env`.

El proyecto existente incluye, entre otros:

- `main.py`: punto de entrada actual.
- `src/core/bot.py`: orquestación de personajes, ciudades y cercados.
- `src/core/adb_controller.py`: controlador que ya contempla ADB, perfiles, ventanas scrcpy y displays.
- `src/core/gestor_personajes.py`: selección de personajes por menú y OCR.
- `src/core/navegador.py`: lectura de coordenadas, navegación, pócimas, Zaapi y cambios de mapa.
- `src/modules/detector_cercado.py`: matching de imágenes para puerta, ventana vacía y popup.
- `src/modules/lector_dragopavos.py`: OCR de tarjetas y contador de filtros.
- `src/modules/gestor_filtros.py`: acciones de UI, selección y drag-and-drop.
- `src/config/`: configuración de perfiles, cercados y filtros.
- `src/utils/`: estado, reportes, logs y utilidades.
- `assets/templates/`: referencias visuales usadas por el detector.
- `tests/`: varios scripts de prueba manual; algunos pueden enviar acciones reales al juego.
- `lanzador/`: código y scripts que gestionan selección de perfiles/personajes, dispositivos y ventanas de scrcpy.

Lee específicamente `lanzador/run.py`, `lanzador/run2.py`, `lanzador/tablets.bat`, `lanzador/tablets.ps1` y `lanzador/seleccion.json` (si existen). No leas `lanzador/logs/` salvo que sea indispensable y el usuario lo autorice. En particular, no reproduzcas seriales, rutas absolutas con nombres de usuario, contenido de logs ni otros datos locales en respuestas o documentación.

### Contexto del lanzador que debes verificar con el código

La carpeta `lanzador/` no es un recurso accesorio: debe integrarse en la solución. Allí existen al menos:

- Un lanzador de línea de comandos que inicia una lista predefinida de perfiles.
- Un lanzador Tkinter que muestra perfiles seleccionables, permite lanzarlos, restaura la selección desde JSON y puede maximizar las ventanas.
- Scripts `.bat` y `.ps1` que inician scrcpy con parámetros diferentes para perfiles del usuario principal y perfiles secundarios.
- Una convención de títulos de ventana que usa prefijos distintos según el tipo de lanzamiento.
- Asociación de perfil a dispositivo y alias.
- Uso de `--new-display` y detección del `display_id` desde los logs de scrcpy; el script PowerShell inicia después la app Android en ese display.
- Dimensiones configuradas para el display Android y tamaño/posición configurados para la ventana de Windows. Estos valores no son intercambiables.

Confirma estos detalles en los archivos y mantenlos coherentes con la configuración de la aplicación. En el estado actual pueden existir definiciones repetidas de dispositivos y perfiles entre `lanzador/`, `src/config/config_perfiles.py` y otros módulos, además de perfiles que no coinciden entre lanzador y bot. Diseña una fuente de verdad adecuada para que el lanzador y el bot compartan los mismos perfiles, aliases, tipos, títulos y dispositivos sin duplicar datos. Migra con cuidado las selecciones existentes si cambia su formato.

Los scripts apuntan a rutas externas y locales que pueden no estar disponibles en otro equipo. No asumas que esos archivos externos existen solo porque el lanzador los referencia. Identifica las dependencias, parametriza rutas y registra con claridad los requisitos; no copies automáticamente configuraciones particulares del equipo a código portable.

### Distinción crítica entre coordenadas

Investiga y documenta explícitamente estos sistemas, sin tratarlos como equivalentes:

1. Coordenadas de píxeles de la captura del display Android donde se ejecuta el juego.
2. Coordenadas de píxeles del área de contenido de la ventana scrcpy en Windows.
3. Coordenadas de pantalla de Windows, que incluyen posición, marco, bordes, barra de título, escala DPI y ventanas maximizadas.
4. Coordenadas lógicas o físicas derivadas de resolución, orientación, densidad y escalado.

Determina cuál fuente se utilizará para capturar imágenes y cuál método se utilizará para enviar las entradas. El sistema debe garantizar que captura, detección y taps/swipes se refieran al mismo personaje, dispositivo, display y geometría. No uses coordenadas relativas a la ventana del PC para ejecutar `adb input` sin una transformación calibrada y probada. Tampoco conviertas coordenadas si la captura y las acciones ya comparten el sistema de coordenadas del display Android.

El usuario pide que la primera prueba responda, con evidencia y no con suposiciones:

- Si se puede reconocer cada ventana scrcpy por su título y asociarla al perfil y dispositivo correcto.
- Cómo obtener el rectángulo real de la ventana y su área cliente, incluidos bordes y decoraciones.
- Si maximizar, mover o escalar la ventana cambia la relación entre coordenadas de Windows y del dispositivo.
- Si se requiere conversión y cuál es la transformación correcta, o si debe evitarse y trabajar enteramente con coordenadas Android.
- Si las capturas de ADB muestran el display virtual donde está el juego y cómo seleccionar ese display.
- Si el `display_id` descubierto por los scripts del lanzador es el que usa tanto la captura como las acciones.
- Cómo detectar resolución, orientación, escala y cambios de geometría, y fallar de forma segura si no coinciden.

No concluyas que la conversión es necesaria o innecesaria hasta probar la ruta real. Añade una visualización/diagnóstico seguro que dibuje el área detectada, ejes, bordes y puntos de referencia sobre la captura/ventana cuando sea posible; no hagas taps reales como parte de esa primera verificación.

### Plan de desarrollo obligatorio, incremental y verificable

Desarrolla y valida cada fase antes de depender de ella en la siguiente. Incluye módulos de prueba con descripción y uso documentados. Organiza los tests automatizados separadamente de los diagnósticos manuales que requieren scrcpy/dispositivo. Los nombres siguientes describen capacidades; adapta la estructura final si encuentras un diseño más simple.

#### Fase 0 — Inventario y diagnóstico técnico

Traza el camino real desde el punto de entrada hasta lanzador, configuración, resolución de perfil/ventana, captura, detección, acciones, navegación, filtros, reportes y estado. Revisa imports, referencias, duplicados, dependencias externas y errores de ejecución.

Entrega una tabla corta de capacidades: existente y funcional según evidencia, incompleta, duplicada, bloqueante o pendiente de validar en dispositivo. Distingue hechos del código de hipótesis. No ejecutes scripts que interactúen con dispositivos.

#### Fase 1 — Lanzador, ventanas scrcpy y coordenadas

Es la primera funcionalidad que debe probarse en dispositivo. Integra el lanzador con el bot y establece la resolución de perfiles/ventanas sin ambigüedad. Prueba reconocimiento de títulos, dispositivo asociado, `display_id`, estado de la ventana y geometría del área cliente.

Prepara dos niveles de prueba:

- Pruebas unitarias con mocks para perfiles, títulos, selección persistida, comando de lanzamiento, asociación ventana/perfil/dispositivo y transformación geométrica.
- Diagnóstico manual seguro, descrito paso a paso, que muestre ventanas detectadas, marco/área cliente, resolución, orientación, display, puntos de referencia y coordenadas calculadas. En esta fase no envíes taps ni swipes automáticamente.

Define criterios de aceptación medibles para decidir si la interacción utilizará coordenadas Android directas o una conversión desde Windows. No inventes una conversión ni uses offsets heredados de LDPlayer como verdad.

#### Fase 2 — Captura y lectura de posición del mapa

Implementa una captura explícita y repetible del display correcto; valida formato, dimensiones, orientación y errores. Prueba lectura OCR de coordenadas con fixtures/capturas autorizadas, distintos signos y errores comunes. Separa extracción de texto y lógica de clasificación para que se puedan probar sin dispositivo.

Criterio de aceptación: lectura confiable de las coordenadas con resultados y confianza estructurados; ante lectura dudosa, captura equivocada o coordenadas inválidas no navegar ni continuar como si la posición fuera conocida.

#### Fase 3 — Detección y uso de pócimas

Prueba la detección visual/OCR de las pócimas para teleportarse, incluyendo template inexistente, baja confianza, inventario cerrado y pócima no visible. Primero valida detección sin clic; luego, solo con autorización, prueba un clic controlado y confirma mediante OCR que se llegó a la ciudad esperada. No uses una coordenada fallback a ciegas.

#### Fase 4 — Zaapi y navegación entre mapas

Valida las transiciones de UI y llegada por estado observado. Prueba las rutas y clasificación de zonas con unit tests. Agrega diagnósticos manuales que describan su impacto y requieran confirmación antes de enviar entradas al dispositivo. Maneja timeout, mapa desconocido y destino no confirmado con detención segura y evidencia suficiente.

#### Fase 5 — Cercados y operaciones con dragopavos

Integra detección de puerta, apertura, lectura de ventana, filtros, selección, drag-and-drop al establo/cercado y popups de confirmación. Valida cada transición antes de ejecutar la siguiente. Centraliza las entradas en el controlador común; ningún módulo debe ejecutar ADB directamente por su cuenta.

Las reglas reales de filtros son reglas de negocio del usuario. Si están vacías, son ejemplos o se contradicen, no las inventes. Pregunta por las reglas faltantes antes de activar una operación que pueda mover dragopavos.

#### Fase 6 — Recorrido total e integración

Solo después de validar todas las fases anteriores, integra el recorrido de cada perfil/personaje y de los cercados configurados en ambas ciudades. Incluye límites claros, pausa/cancelación, checkpoint/resume si se requiere, detección de errores, reportes y recuperación segura. Ejecuta primero un modo de simulación o dry-run que muestre acciones sin enviarlas; habilita una corrida real de forma explícita y con el usuario presente.

Criterio de aceptación: el sistema identifica la ventana y display correctos, navega al destino, valida cada estado, opera solamente según filtros confirmados, registra resultados y se detiene ante cualquier estado inesperado. No declares integración completa si alguna ciudad, personaje o cercado no fue probado.

### Diseño de pruebas requerido

Para cada fase crea o adapta módulos de test que describan:

- Qué se prueba y qué no.
- Requisitos previos y configuración local.
- Si es una prueba unitaria/mock o una prueba manual en dispositivo real.
- Qué comandos la ejecutan y qué resultado se espera.
- Si puede modificar el estado del juego.
- Cómo se evita hacer acciones en un perfil incorrecto.

Mantén las pruebas que requieren dispositivo claramente separadas y con nombres que adviertan su carácter interactivo. Las pruebas automáticas por defecto nunca deben conectarse a un dispositivo ni enviar inputs. Usa capturas de prueba anonimizadas o sintéticas y mocks de ADB/scrcpy en CI. No agregues un test “de prueba” que haga clic de inmediato al ejecutarse.

### Requisitos de arquitectura y calidad

- Separa lanzador/interfaz, configuración de perfiles, transporte/captura, transformación de coordenadas, percepción visual, lógica del juego, orquestación y reportes.
- Elige una única interfaz de controlador de pantalla para capturas, taps, swipes, doble taps y teclas. No permitas llamadas ADB sueltas en los módulos de negocio.
- Haz explícito el contexto de personaje/dispositivo/display en las operaciones. Si la ventana está ausente, el perfil es ambiguo, el display no se conoce o el dispositivo está desconectado, no ejecutes la acción.
- Usa rutas portables y configuración compartida entre lanzador y bot. No guardes rutas personales, seriales reales o secretos como defaults comprometidos.
- Centraliza resolución, calibración, umbrales, regiones de OCR/templates y tiempos. No disperses coordenadas mágicas o compensaciones por el proyecto.
- La percepción debe diferenciar claramente error de captura, elemento no detectado, pantalla vacía y resultado válido. Conserva confianza, dimensiones y origen de coordenadas cuando sean útiles.
- Prefiere esperar una transición visual confirmable a pausas fijas; limita reintentos y registra errores explícitos.
- Separa lógica pura (rutas, filtros, parsers, clasificación) de operaciones sobre Android.
- Evita duplicación, pero verifica dependencias antes de borrar archivos. Puedes retirar módulos obsoletos/duplicados una vez que confirmes que no se usan y actualices referencias y documentación.
- Conserva o mejora logs, estado y reportes sin incluir datos sensibles ni producir capturas de depuración permanentes innecesarias.
- Sigue las convenciones presentes, utiliza tipado cuando aporte claridad, maneja errores explícitamente y ejecuta las pruebas/linter/type-check disponibles.
- No agregues dependencias salvo necesidad demostrada. No afirmes que probaste una función si solo la inspeccionaste.
- Mantén la automatización dentro de las reglas de uso aplicables al juego y no desarrolles mecanismos para evadir anti-cheat, CAPTCHA o restricciones de acceso.

### Autonomía, preguntas y uso de agentes

Tienes vía libre para modificar, crear, reorganizar o eliminar código y módulos en favor de la solución más compacta y mantenible. Antes de un cambio importante, conserva las capacidades necesarias, verifica referencias y añade pruebas que justifiquen el nuevo comportamiento. Expón el plan por fases y ejecuta cambios coherentes; no pidas permiso para cada refactor interno.

Pregunta únicamente cuando falte una decisión del usuario que no pueda deducirse ni validarse de manera segura, por ejemplo: reglas de filtrado reales, comportamiento deseado ante límites de capacidad, permiso para una prueba interactiva o decisión de negocio sobre personajes. Para detalles técnicos que se puedan observar en el código o medir sin riesgo, investiga primero.

Si la plataforma ofrece agentes, puedes utilizarlos para actividades independientes y bien delimitadas (por ejemplo, auditar la configuración del lanzador mientras otro analiza la estrategia de tests), siempre que no compartan ediciones concurrentes. Integra críticamente los resultados; no aceptes conclusiones sin verificar y no dividas artificialmente una sola traza del flujo principal.

### Entregables

Al inicio:

1. Resumen de arquitectura y flujo actual, incluyendo la carpeta `lanzador/`.
2. Hallazgos priorizados: bloqueantes, riesgos operativos y deuda técnica.
3. Diagrama o descripción del camino de datos: ventana/perfil → dispositivo/display → captura → coordenadas → percepción → acción → validación.
4. Plan por fases con criterios de aceptación y tests correspondientes.
5. Preguntas imprescindibles, solo si realmente bloquean avanzar.

Durante el trabajo:

- Implementa los cambios en el workspace si tienes acceso.
- Mantén el lanzador y el bot coherentes y elimina configuración duplicada cuando sea seguro.
- Añade documentación de uso y descripción de cada módulo de test.
- Valida cada fase con pruebas no interactivas antes de proponer una prueba real.

Al finalizar:

- Resume qué cambió, qué archivos o módulos se consolidaron/eliminaron y por qué.
- Lista las pruebas ejecutadas y sus resultados reales.
- Distingue claramente las pruebas unitarias de las pruebas manuales aún pendientes.
- Explica cómo ejecutar el modo diagnóstico y, cuando esté autorizado, la corrida integrada.
- Indica lo que sigue pendiente por falta de datos, assets o validación en dispositivo.

No leas ni pegues secretos de `.env`. No incluyas seriales, rutas personales, logs privados ni credenciales en respuestas, documentación o código compartido.

---

## Información opcional para completar

Usa primero lo que puedas confirmar en `lanzador/` y en el resto del workspace. No vuelvas a preguntarme por datos que ya estén claramente definidos allí. Pregunta solo por valores que no estén disponibles o requieran una decisión mía:

- Reglas exactas de filtros por tipo de cercado, si todavía no están definidas en el proyecto.
- Confirmación para ejecutar pruebas interactivas en dispositivos reales y qué perfil/dispositivo puede usarse como prueba.
- Cualquier resultado manual que no pueda obtenerse desde el código: por ejemplo, si la captura ADB coincide visualmente con la ventana del juego, una vez que el diagnóstico esté listo.
