"""
Orion Tool — Capture d'écran cross-platform via mss + Pillow.

Capture full screen, monitor spécifique, ou région (x, y, width, height).
Sauvegarde PNG dans data/screenshots/ par défaut.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .automation import ensure_dpi_aware

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DIR = ROOT / "data" / "screenshots"

# Sans ça, sur écran mis à l'échelle (125 %, 150 %), l'image capturée n'est pas
# dans le même repère que la souris et tous les clics dérivés tombent à côté.
ensure_dpi_aware()


def screenshot(
    path: str | None = None,
    monitor: int = 0,
    region: dict | None = None,
    return_base64: bool = False,
    max_width: int | None = None,
) -> dict:
    """Capture d'écran. region = {x, y, width, height} (optionnel).

    max_width : si fourni et que la capture est plus large, l'image est réduite.
    Le résultat contient alors 'scale' et 'coordinate_hint' : les coordonnées à
    passer aux tools souris sont celles du BUREAU, pas celles de l'image réduite.
    """
    try:
        import mss
        import mss.tools
    except ImportError:
        return {
            "success": False,
            "error": "mss n'est pas installé. Installe avec :\n"
                     "    pip install -r requirements-extras.txt",
        }

    if path is None:
        DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
        path = str(DEFAULT_DIR / f"orion_{datetime.now():%Y%m%d_%H%M%S}.png")
    else:
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    try:
        with mss.mss() as sct:
            if region and all(k in region for k in ("x", "y", "width", "height")):
                bbox = {
                    "left": int(region["x"]),
                    "top": int(region["y"]),
                    "width": int(region["width"]),
                    "height": int(region["height"]),
                    "mon": int(monitor) if monitor else 1,
                }
            else:
                # monitor=0 = tous les écrans combinés, 1+ = écran spécifique
                idx = int(monitor) if monitor and monitor < len(sct.monitors) else 0
                bbox = sct.monitors[idx]
            shot = sct.grab(bbox)
            full_w, full_h = shot.size
            scale = 1.0
            if max_width and full_w > int(max_width):
                from PIL import Image
                scale = int(max_width) / full_w
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                img = img.resize((int(max_width), max(1, int(full_h * scale))),
                                 Image.LANCZOS)
                img.save(path, format="PNG", optimize=True)
                out_w, out_h = img.size
            else:
                mss.tools.to_png(shot.rgb, shot.size, output=path)
                out_w, out_h = full_w, full_h
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    origin_x, origin_y = bbox["left"], bbox["top"]
    result = {
        "success": True,
        "path": path,
        "size": {"width": out_w, "height": out_h},
        "captured_size": {"width": full_w, "height": full_h},
        "origin": {"x": origin_x, "y": origin_y},
        "scale": round(scale, 4),
    }
    if scale != 1.0:
        result["coordinate_hint"] = (
            f"Image réduite. Pour cliquer : x_bureau = {origin_x} + x_image/{scale:.4f}, "
            f"y_bureau = {origin_y} + y_image/{scale:.4f}."
        )
    elif origin_x or origin_y:
        result["coordinate_hint"] = (
            f"Origine de la capture au point bureau ({origin_x},{origin_y}) : "
            f"ajouter cet offset aux coordonnées lues sur l'image."
        )
    if return_base64:
        import base64
        with open(path, "rb") as f:
            result["base64"] = base64.b64encode(f.read()).decode("ascii")

    # Maintenance non bloquante : purge automatique des anciennes captures
    try:
        from server.tools.capture_rotation import rotate_captures
        rotate_captures(max_files=100, max_age_days=7)
    except Exception:
        pass

    return result


def list_monitors() -> dict:
    """Liste les écrans détectés."""
    try:
        import mss
        with mss.mss() as sct:
            mons = []
            for i, m in enumerate(sct.monitors):
                mons.append({
                    "index": i,
                    "width": m["width"],
                    "height": m["height"],
                    "left": m["left"],
                    "top": m["top"],
                    "primary": i == 1,
                    "all_screens": i == 0,
                })
        return {"success": True, "monitors": mons}
    except ImportError:
        return {"success": False, "error": "mss n'est pas installé."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def screen_ocr(
    region: dict | None = None,
    monitor: int = 0,
    title_contains: str | None = None,
    prompt: str = "Lis et retranscris tout le texte visible sur cette image.",
) -> dict:
    """Effectue un OCR de l'écran, d'une région ou d'une fenêtre ("lis-moi cette erreur").

    Utilise pytesseract si disponible ou s'appuie sur l'API Vision LLM d'Orion.
    """
    if title_contains:
        try:
            from server.tools.windows_ctrl import _import_gw, _find
            gw = _import_gw()
            if gw:
                w = _find(gw, title_contains)
                region = {"x": w.left, "y": w.top, "width": w.width, "height": w.height}
        except Exception:
            pass

    snap_res = screenshot(monitor=monitor, region=region)
    if not snap_res.get("success"):
        return snap_res

    image_path = snap_res["path"]

    tesseract_text = None
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        tesseract_text = pytesseract.image_to_string(img).strip()
    except Exception:
        pass

    from server.tools.vision import analyze_image
    vision_res = analyze_image(path=image_path, prompt=prompt)

    extracted_text = tesseract_text or vision_res.get("description", "")

    return {
        "success": True,
        "path": image_path,
        "method": "tesseract" if tesseract_text else vision_res.get("provider", "vision"),
        "text": extracted_text,
        "tesseract_raw": tesseract_text,
        "vision_analysis": vision_res.get("description"),
    }


HANDLERS = {
    "screenshot": lambda p: screenshot(**p),
    "list_monitors": lambda p: list_monitors(),
    "screen_ocr": lambda p: screen_ocr(**p),
}

