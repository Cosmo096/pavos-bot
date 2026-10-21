# Diagnóstico del proyecto y ruta por fases

## Alcance de esta iteración

Se inspeccionó el código y la configuración del workspace, no `.env` ni logs. No se
ejecutaron lanzadores, pruebas manuales, ADB, scrcpy, taps ni swipes. La evidencia
de esta revisión es estática, salvo las pruebas unitarias indicadas al final.

## Arquitectura y flujo actual

```text
lanzador Python
  -> perfil compartido (alias/dispositivo, tipo, título)
  -> tablets.bat o tablets.ps1
  -> scrcpy local con --new-display
  -> título exacto de ventana + log de scrcpy -> HWND y display_id
  -> controlador ADB -> captura screencap -d / input -d
  -> OCR y template matching -> navegación y filtros -> reporte/estado
```

El controlador ya tiene mecanismos para resolver ventanas por título exacto y
para asociar el perfil con su dispositivo y el `display_id` leído del log. El
diagnóstico nuevo aprovecha esa resolución y captura explícitamente el display
del perfil. No se utiliza una API web para abrir scrcpy: scrcpy es un proceso
local y necesita `scrcpy.exe`; un servicio/API remoto requeriría instalar y
mantener un agente local propio. El ejecutable queda configurable con
`SCRCPY_DIR`.

### Sistemas de coordenadas (no equivalentes)

1. **Display Android**: píxeles de la captura del juego y sistema de `adb input`.
   El controlador puede pasar el mismo `display_id` a captura e input.
2. **Área cliente scrcpy**: píxeles que presenta la ventana después de su escala
   de renderizado; se mide con `GetClientRect` y `ClientToScreen`.
3. **Pantalla Windows**: coordenadas absolutas que incluyen la posición de la
   ventana. `GetWindowRect` incluye marco y decoraciones; maximizar y DPI pueden
   cambiar los rectángulos o la escala observada.
4. **Resolución/densidad Android**: el lanzador define un display virtual de
   `2560x1440/320`, mientras que `1920x1080` y `(15,15)` son tamaño/posición
   iniciales de la ventana Windows. No son dimensiones intercambiables.

Las acciones de negocio deben utilizar coordenadas Android y el `display_id`
explícito. No se implementó ni se usa una conversión Windows→Android. La captura
marcada y la ventana marcada permiten comparar puntos visuales, pero la relación
entre ambas sigue pendiente de validación manual. Si el display no se resuelve,
la captura falla o los puntos no coinciden, no se debe actuar.

## Inventario basado en código

| Área | Estado observado | Evidencia / limitación |
|---|---|---|
| Lanzador CLI y Tkinter | Incompleta; consolidada parcialmente | Los dos tenían listas distintas; ahora ambas usan IDs de perfil comunes y conservan sus subconjuntos. |
| Scrcpy, display y títulos | Parcial | BAT usa usuario principal y `--start-app`; PowerShell usa usuario secundario y abre la app en el display detectado. No se comprobó en un Android real. |
| Perfil, ventana y controlador ADB | Parcial | El controlador resuelve título exacto y display desde log; las operaciones de captura del bot no siempre solicitan el display virtual. |
| Geometría Windows | Parcial | El diagnóstico nuevo mide marco, área cliente y DPI, y guarda imágenes anotadas. Esas medidas aún no demuestran una transformación válida. |
| Captura Android | Parcial | Hay captura ADB por display; el bot usa por defecto la pantalla principal. Debe integrarse con un contexto de perfil explícito. |
| OCR de mapa/navegación | Bloqueante para automatización | Hay OCR y validaciones, pero existen fallbacks que asumen una ubicación aun si no se confirma el resultado. |
| Pócimas | Pendiente | El código puede usar coordenadas fallback; los templates de pócima referenciados no aparecen en el inventario de assets. |
| Cercados/templates | Parcial | Hay templates genéricos; falta validar resolución, escala y detección por ciudad en capturas autorizadas. |
| Filtros y movimiento de dragopavos | Bloqueante | Hay reglas lógicas por cercado y revalidación pura de serenidad/cansancio, pero no están conectadas al OCR. Las coordenadas heredadas no están calibradas para scrcpy y la UI falla cerrada; el bot sigue deshabilitado. |
| Reporte/estado | Parcial | Hay reportes y JSON de progreso; `guardar_estado` está definido dos veces y el progreso no se usa para reanudar el flujo actual. |
| Pruebas | Parcial | `tests/` contiene diagnósticos/scripts manuales; no estaban separados de una suite automática. Se añadieron pruebas puras en `tests/unit/`. |

## Hallazgos priorizados

### Bloqueantes

1. No existen reglas operativas configuradas en `src/config/filtros.py`. No se
   deben mover dragopavos hasta recibir esas reglas.
2. `gestor_filtros.py` manda un swipe ADB por su cuenta a un dispositivo fijo;
   no comparte el contexto de perfil/display ni respeta el controlador común.
3. `bot.py` usa una lista de personajes distinta de los perfiles del lanzador y
   no entrega un perfil inequívoco a todas las operaciones.
4. La captura por defecto no solicita el display virtual, aunque las acciones
   puedan incluir `-d display_id`. Captura y acción podrían observar pantallas
   diferentes.

### Riesgos operativos altos

- El inicio del perfil principal ejecuta `am force-stop` si detecta el juego en
  primer plano; el perfil secundario también ejecuta `force-stop` para su
  usuario. Lanzar scrcpy no es, por tanto, una prueba puramente pasiva.
- El flujo de pócima puede acabar usando una coordenada fija y asumir el centro
  aunque no haya una lectura OCR confirmada.
- Las coordenadas y regiones de OCR/templates provienen de supuestos de otra
  geometría; la captura de `2560x1440` virtual aún no se contrastó con la UI.
- El código existente de las pruebas manuales puede enviar acciones reales. No
  se ejecutó ninguno.

### Cambios de esta iteración

- Un solo catálogo compartido en `src/config/config_perfiles.py` conserva los
  perfiles de GUI y CLI mediante IDs estables. También concentra títulos,
  tamaño/densidad del display y geometría inicial de ventana.
- Los seriales de ADB y la ruta local de scrcpy salen del código. Se carga el
  `.env` local sin leerlo ni modificarlo. `seleccion.json` conserva compatibilidad:
  las claves anteriores se migran en memoria usando nombre y tipo y las nuevas
  escrituras usan IDs estables.
- BAT y PowerShell reciben título y geometría desde el lanzador. El parser de
  `display_id` faltante se agregó localmente como `get_display_id.ps1`; la ruta
  externa que antes se referenciaba ya no se necesita.
- Se corrigió el import del controlador al paquete `src.config`.
- `diagnostico_scrcpy.py` es solo lectura: requiere una ventana/perfil existente,
  captura el display asociado, consulta marco/área cliente/DPI y escribe dos
  imágenes anotadas en rutas explícitas. No envía entradas.
- Se añadió una regla pura de revalidación por tipo de cercado: usa los límites
  de serenidad confirmados, asigna -1999 y 1999 a Madurez, y rechaza cansancio
  de 100%, lecturas ausentes y valores fuera de rango. Aún no está conectada a
  OCR ni a los movimientos del bot.
- Los filtros de preselección se organizan por ID estable de cercado y cubren
  gota/rayo/corazón, Aguante/Amor/Madurez y cansancio menor de 100%. Sus
  controles visuales no están calibrados: las coordenadas de gota/rayo/corazón
  y cansancio son `None`, y las coordenadas heredadas se bloquean mediante
  `COORDENADAS_UI_CALIBRADAS = False`. Ninguna función de filtro o movimiento
  envía una entrada mientras esa precondición siga falsa.
- El gestor de filtros ya no ejecuta ADB por separado: los swipes usan el
  controlador común. El popup de capacidad no se confirma a ciegas; la captura
  fallida o la falta de coordenada del botón producen un error antes de tocarlo.
- La entrada `main.py` ya no deja el proceso esperando tras un ciclo síncrono;
  la ejecución real queda cerrada por una precondición explícita hasta integrar
  el lector/revalidador visual y validar el flujo.

No se eliminaron los módulos `copy`: no se hizo una limpieza de duplicados sin
un rastreo de referencias suficiente.

### Requisito funcional aclarado: filtros y validación individual

El filtro de interfaz es solo una preselección: cada cercado puede tener una
combinación distinta de botones; el resultado puede contener cero, uno o varios
dragopavos. Como la interfaz puede devolver candidatos incorrectos, el bot debe
revisar cada tarjeta y contrastar su barra/estadística con el rango y tolerancia
del cercado antes de moverla. Solo las tarjetas que superen esa validación se
pueden arrastrar.

La especificación aportada define estos bloques; la correspondencia entre
“bajar/subir serenidad” y los cercados actuales de tristeza/felicidad se debe
configurar como tristeza→bajar serenidad y felicidad→subir serenidad, además de
los bloques de resistencia, madurez y amor descritos abajo. Brakmar prioriza
hembras y Bonta machos en los cercados de amor/resistencia; esa restricción ya
está representada en `src/config/cercados.py`.

| Bloque | Filtros declarados | Condición de barra declarada |
|---|---|---|
| Bajar serenidad (Bofetadores) | Aguante, gota, corazón, cansancio <100% | Mayor que -1999 |
| Subir serenidad (Acariciadores) | Amor, rayo, gota, cansancio <100% | Menor que 1999 |
| Aguante/Resistencia (Fulminadoras) | Aguante, rayo, cansancio <100% | -10000 a -1999 |
| Madurez (Abrevaderos) | Madurez, gota, cansancio <100% | -1999 a 1999 |
| Amor (Dragnalgas) | Amor, corazón, cansancio <100% | 1999 a 10000 |

También se especificaron requisitos de reproducción: madurez al máximo, nivel
5 o superior, Aguante y Amor de al menos 7500, pareja macho/hembra de la misma
especie y retorno de ambos al establo al confirmar la hembra como fecundada.
Cada cercado tiene capacidad de 10. El usuario confirmó que, para Amor y
Resistencia, se mantiene la prioridad sexual por ciudad descrita arriba. El
límite del establo/cercado y el popup deben verificarse antes de decidir qué
hacer con una selección mayor.

El lector OCR actual intenta leer nombres, niveles y el contador, no la barra por
tarjeta, cansancio, especie ni estado de fecundación. La lógica pura nueva cubre
únicamente la comprobación de serenidad/cansancio cuando esos valores ya se
conocen; aún no los obtiene de la pantalla ni condiciona el movimiento del bot.
Las coordenadas existentes no identifican por separado gota/rayo/corazón ni el
filtro <100%; tampoco se conoce la coordenada del botón “OK” del popup. No se
usará una posición aproximada para esos controles.

Los extremos quedaron definidos: -1999 y 1999 se clasifican como Madurez; el
rango de Resistencia excluye -1999 y el de Amor excluye 1999. El mapeo por tipo
es tristeza→bajar serenidad, felicidad→subir serenidad, y los demás tipos a su
bloque homónimo. Sigue pendiente comprobar los controles reales y conectar una
observación por tarjeta. Hasta entonces el filtro de UI solo puede tratarse
como preselección; cero resultados es válido y una tarjeta no verificada nunca
se debe mover.

## Plan por fases y aceptación

| Fase | Trabajo/aceptación | Tests y estado |
|---|---|---|
| 0. Inventario | Trazar flujo, duplicados, requisitos y riesgos; separar hechos de validación pendiente. | Completada por inspección; sin ejecutar código de dispositivo. |
| 1. Lanzador/ventanas | Perfiles con IDs estables; título único; vínculo al dispositivo y display; medir marco/cliente/DPI. No convertir coordenadas ni enviar acciones. | Unit tests de perfiles/comandos/rectángulos; diagnóstico manual preparado, pendiente con ventana y dispositivo. |
| 2. Captura/posición | Capturar el display explícito; validar dimensiones/formato y hacer parser OCR puro con confianza; lectura dudosa detiene navegación. | Fixtures unitarios sintéticos/anonimizados y prueba manual separada por dispositivo. |
| 3. Pócimas | Detectar sin clic y sin fallback ciego; validar destino observado. | Templates/capturas pendientes; cualquier clic requiere autorización explícita. |
| 4. Zaapi/rutas | Rutas puras unit-test; transiciones por estado observado; detenerse en timeout/mapa desconocido. | Tests puros + prueba manual confirmada antes de entradas. |
| 5. Cercados | Configuración individual por cercado; el resultado del filtro es solo candidato; validar barra de cada tarjeta contra rango/tolerancia y mover únicamente las aceptadas. | Reglas lógicas por ID de cercado y revalidación pura implementadas y probadas. Sigue bloqueada por falta de lector visual por tarjeta, coordenadas de filtros no verificadas y flujo de capacidad/reproducción. |
| 6. Integración | Dry-run, cancelación, límites, checkpoint/resume y habilitación real explícita. | No iniciada; depende de las fases anteriores. |

### Diagnóstico manual de Fase 1 (sin taps/swipes)

**Requisitos previos**: Windows, Python con `requirements.txt`, ADB instalado y
autorizado, `.env` local configurado, un perfil scrcpy ya abierto y su log local
con `display_id`. La ruta de captura debe tener espacio disponible y no
sincronizarse/compartirse: las imágenes pueden contener datos del juego.

1. Copia `.env.example` a `.env` y agrega localmente los valores requeridos.
2. No abras el lanzador para esta comprobación sin autorización: los scripts de
   inicio pueden detener la app. Usa una ventana ya iniciada y confirma qué
   perfil está activo.
3. Ejecuta el diagnóstico desde PowerShell, por ejemplo:

   ```powershell
   python lanzador\diagnostico_scrcpy.py `
     --profile panda-secondary `
     --capture-output "$env:TEMP\dragopavo-display.png" `
     --window-output "$env:TEMP\dragopavo-window.png"
   ```

4. Comprueba que informa el título esperado, un `HWND`, un `display_id`, estado
   ADB conectado y dimensiones positivas. La captura Android muestra ejes y
   referencias de 25/50/75%; la imagen de Windows marca en rojo el marco y en
   verde el área cliente.
5. Compara visualmente los mismos elementos en ambas imágenes. Si la ventana se
   mueve, restaura o maximiza, vuelve a ejecutar el diagnóstico y compara
   dimensiones/rectángulos. No se hace ningún tap ni swipe.
6. Acepta coordenadas Android directas solo después de verificar que captura e
   input usan el mismo dispositivo/display y que las referencias visuales
   coinciden. Si no se puede probar, no habilites automatización. El diagnóstico
   no deriva una transformación Windows→Android.
7. Elimina manualmente las dos imágenes locales cuando ya no sean necesarias.
   No se crean capturas de depuración adicionales automáticamente.

La captura de pantalla del escritorio puede estar vacía o restringida por el
renderizador/OpenGL. En ese caso el informe de rectángulos sigue siendo útil,
pero la comparación visual no se considera aceptada.

## Configuración local y ejecución

Variables que deben mantenerse fuera del código:

- `ADB_DEVICE_TABLET` y `ADB_DEVICE_TABLET_PRO`: seriales/identificadores locales
  de ADB.
- `SCRCPY_DIR`: ruta local que contiene `scrcpy.exe` (dato de entorno, no secreto
  de autenticación, pero no portable).

No guardes contraseñas, tokens, claves ni seriales reales en el repositorio. ADB
debe estar disponible en `PATH`. No hay API online de scrcpy que sustituya al
ejecutable local.

Pruebas de código, que no requieren ni conectan dispositivos:

```powershell
python -m unittest discover -s tests\unit -p "test_*.py" -v
```

`tests/unit/test_filter_configuration.py` comprueba que cada cercado tenga una
regla asociada y que los filtros, selección y swipes fallen sin tocar el
dispositivo mientras la UI no esté calibrada. También comprueba el cierre seguro
si aparece un popup sin botón de confirmación calibrado. Son pruebas unitarias
con mocks: no requieren scrcpy ni pueden cambiar el estado del juego.

El lanzador Tkinter se inicia con `python lanzador\run2.py`. Este comando sí
inicia procesos scrcpy y puede afectar el estado de la app, por lo que no se
ejecutó aquí. El CLI `python lanzador\run.py` lanza su subconjunto predefinido
y tampoco debe ejecutarse como prueba unitaria.

## Pendiente antes de automatizar

- Medir en la interfaz los botones de serenidad, cansancio y confirmación; no se
  deducen coordenadas de la UI anterior.
- Implementar la percepción por tarjeta (serenidad, cansancio, nivel, especie,
  estadísticas y estado fecundado) y conectar la función pura de revalidación.
- Acordar qué personaje del lanzador corresponde a cada personaje procesado
  por el bot. Los nombres del bot y los IDs de los perfiles son distintos; no
  se encontró esa relación en los archivos inspeccionados.
- Ejecutar el diagnóstico en un perfil elegido y revisar las dos imágenes.
- Confirmar soporte real de `screencap -d` y `input -d` para el display virtual
  creado por la versión local de scrcpy.
- Propagar el perfil/personaje explícito a todas las acciones y corregir la
  captura por defecto; eliminar fallbacks de navegación no confirmados.
- Diseñar e implementar la lectura/validación por tarjeta con resultados
  estructurados y pruebas de cero/una/varias coincidencias. El login opcional
  desde `run2.py` queda para después de validar la ventana/display y requiere
  una acción de UI explícita; no se añadió en esta fase.
- Validar capturas, templates, OCR, Zaapi y cercados en dispositivo antes de
  declarar completa cualquier ciudad o recorrido.
