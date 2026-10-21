from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
from PIL import ImageDraw, ImageGrab

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.config_perfiles import perfiles
from src.core.adb_controller import ControladorADB
from src.core.window_geometry import leer_geometria_ventana


def _marcar_captura_android(path: Path) -> tuple[int, int]:
    image = cv2.imread(str(path))
    if image is None:
        raise RuntimeError(f"No se pudo leer la captura Android: {path}")
    height, width = image.shape[:2]
    cv2.line(image, (0, 0), (width - 1, 0), (0, 255, 0), 2)
    cv2.line(image, (0, 0), (0, height - 1), (0, 255, 0), 2)
    for percent in (25, 50, 75):
        point = (width * percent // 100, height * percent // 100)
        cv2.drawMarker(image, point, (0, 0, 255), cv2.MARKER_CROSS, 28, 2)
        cv2.putText(
            image,
            f"{percent}% ({point[0]},{point[1]})",
            (point[0] + 8, point[1] - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 255),
            1,
        )
    cv2.putText(
        image,
        f"Android display pixels: {width}x{height}",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"No se pudo guardar la captura anotada: {path}")
    return width, height


def _guardar_captura_ventana(frame: tuple[int, int, int, int], client: tuple[int, int, int, int], path: Path) -> tuple[int, int]:
    image = ImageGrab.grab(bbox=frame, all_screens=True)
    draw = ImageDraw.Draw(image)
    frame_left, frame_top, _, _ = frame
    client_left, client_top, client_right, client_bottom = client
    client_box = (
        client_left - frame_left,
        client_top - frame_top,
        client_right - frame_left,
        client_bottom - frame_top,
    )
    draw.rectangle((0, 0, image.width - 1, image.height - 1), outline="red", width=3)
    draw.rectangle(client_box, outline="lime", width=3)
    client_width = client_right - client_left
    client_height = client_bottom - client_top
    for percent in (25, 50, 75):
        x = client_box[0] + client_width * percent // 100
        y = client_box[1] + client_height * percent // 100
        draw.line((x - 12, y, x + 12, y), fill="blue", width=2)
        draw.line((x, y - 12, x, y + 12), fill="blue", width=2)
    image.save(path)
    return image.size


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnóstico visual scrcpy/ADB de solo lectura; no envía taps ni swipes."
    )
    parser.add_argument(
        "--profile",
        required=True,
        choices=[profile["id"] for profile in perfiles],
        help="ID de perfil definido en la configuración compartida.",
    )
    parser.add_argument(
        "--capture-output",
        required=True,
        type=Path,
        help="Ruta explícita para guardar la captura Android anotada.",
    )
    parser.add_argument(
        "--window-output",
        required=True,
        type=Path,
        help="Ruta explícita para guardar la captura de la ventana scrcpy anotada.",
    )
    args = parser.parse_args()
    if args.capture_output.resolve() == args.window_output.resolve():
        parser.error("Las rutas de captura Android y de ventana deben ser distintas.")

    perfil = next(profile for profile in perfiles if profile["id"] == args.profile)
    titulo = perfil["ventana_titulo"]
    controller = ControladorADB()
    context = controller.resolver(titulo)
    if context.display_id is None:
        raise RuntimeError("No hay display_id confirmado para este perfil.")
    if not controller.verificar_conexion(titulo):
        raise RuntimeError("El dispositivo del perfil no está conectado y autorizado.")
    display_properties = controller.consultar_propiedades_display(titulo)

    args.capture_output.parent.mkdir(parents=True, exist_ok=True)
    args.window_output.parent.mkdir(parents=True, exist_ok=True)
    capture_path = controller.tomar_captura(
        str(args.capture_output),
        personaje=titulo,
        display_captura="auto",
    )
    if capture_path is None:
        raise RuntimeError("Falló la captura del display asignado al perfil.")

    geometry = leer_geometria_ventana(context.hwnd)
    display_size = _marcar_captura_android(args.capture_output)
    orientation = (
        "landscape"
        if display_size[0] > display_size[1]
        else "portrait" if display_size[1] > display_size[0] else "square"
    )
    frame = (
        geometry.frame.left,
        geometry.frame.top,
        geometry.frame.right,
        geometry.frame.bottom,
    )
    client = (
        geometry.client.left,
        geometry.client.top,
        geometry.client.right,
        geometry.client.bottom,
    )
    window_image_size = _guardar_captura_ventana(
        frame, client, args.window_output
    )

    print(f"Perfil: {perfil['id']}")
    print(f"Título exacto: {context.titulo}")
    print(f"HWND: {context.hwnd}")
    print(f"display_id: {context.display_id}")
    print(f"Marco Windows (LTRB): {frame}")
    print(f"Área cliente Windows (LTRB, pantalla): {client}")
    print(f"Área cliente: {geometry.client.width}x{geometry.client.height}")
    print(f"DPI reportado por Windows: {geometry.dpi or 'no disponible'}")
    print(f"Captura Android/display: {display_size[0]}x{display_size[1]}")
    print(f"Orientación inferida de captura: {orientation}")
    for name, (ok, detail) in display_properties.items():
        print(f"{name} ({'OK' if ok else 'no disponible'}): {detail}")
    print(f"Imagen ventana anotada: {window_image_size[0]}x{window_image_size[1]}")
    print(f"Captura Android anotada: {args.capture_output}")
    print(f"Ventana anotada: {args.window_output}")
    print("No se calculó ninguna conversión ni se enviaron entradas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
