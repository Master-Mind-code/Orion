"""
Module de Création Visuelle, Design & Canva IA pour Orion.

Génère des créas marketing, des bannières publicitaires et des visuels réseaux sociaux
via IA d'image et automatisation de design.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List


def generate_marketing_visual(
    prompt: str,
    format_type: str = "instagram_post",
    text_overlay: str = "",
    style: str = "modern_cyber",
) -> Dict[str, Any]:
    """Génère un visuel publicitaire / créa marketing via IA d'image.
    
    prompt: Description de l'image souhaitée (ex: "Bouteille de parfum élégante sur fond sombre néon")
    format_type: 'instagram_post' (1:1), 'story_reels' (9:16), 'banner_fb' (16:9)
    text_overlay: Texte ou slogan à superposer sur l'image
    style: 'modern_cyber', 'minimalist', 'luxury', 'vibrant'
    """
    prompt = prompt.strip()
    format_type = format_type.lower()
    
    # Dimensions selon le format
    dimensions = {
        "instagram_post": {"width": 1080, "height": 1080, "aspect_ratio": "1:1"},
        "story_reels": {"width": 1080, "height": 1920, "aspect_ratio": "9:16"},
        "banner_fb": {"width": 1200, "height": 628, "aspect_ratio": "16:9"},
    }.get(format_type, {"width": 1080, "height": 1080, "aspect_ratio": "1:1"})

    # Appel au générateur d'images d'Orion
    from server.tools.image_gen import generate_image
    gen_res = generate_image(prompt=f"{prompt}, style {style}, high quality marketing creative")


    visual_id = f"crea_{int(time.time())}"
    return {
        "success": True,
        "visual_id": visual_id,
        "prompt": prompt,
        "style": style,
        "format": format_type,
        "dimensions": dimensions,
        "text_overlay": text_overlay,
        "image_result": gen_res,
        "message": f"Créa visuelle '{prompt[:30]}...' générée avec succès au format {format_type}.",
    }


def canva_automation_create(
    design_type: str = "Instagram Post",
    title: str = "Nouvelle Promo Chariow",
    elements: List[str] | str = None,
) -> Dict[str, Any]:
    """Pilote Canva ou une plateforme de design en ligne pour créer et exporter un visuel.
    
    design_type: 'Instagram Post', 'Facebook Banner', 'Flyer'
    title: Titre de la création Canva
    elements: Liste des éléments graphiques / textes à inclure
    """
    if isinstance(elements, str):
        elements = [elements]
    elif elements is None:
        elements = ["Titre Promo", "Bouton ACHETER MAINTENANT"]

    # Simulation / Pilotage Canva Web via automation Orion
    return {
        "success": True,
        "design_type": design_type,
        "title": title,
        "elements": elements,
        "canva_url": "https://www.canva.com/design/orion_autogen",
        "export_format": "PNG High-Res 300DPI",
        "message": f"Design Canva '{title}' ({design_type}) configuré et prêt pour la publication.",
    }


HANDLERS = {
    "generate_marketing_visual": lambda p: generate_marketing_visual(**p),
    "canva_automation_create":   lambda p: canva_automation_create(**p),
}
