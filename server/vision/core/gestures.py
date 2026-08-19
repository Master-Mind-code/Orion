# -*- coding: utf-8 -*-
"""Reconnaissance de gestes à partir du motif de doigts levés (cvzone)."""

# Motif [pouce, index, majeur, annulaire, auriculaire] -> nom du geste.
GESTES = {
    (0, 0, 0, 0, 0): "Poing",
    (1, 1, 1, 1, 1): "Main ouverte",
    (0, 1, 0, 0, 0): "Index",
    (0, 1, 1, 0, 0): "Victoire",
    (1, 0, 0, 0, 0): "Pouce leve",
    (0, 0, 0, 0, 1): "Auriculaire",
    (1, 1, 0, 0, 1): "Cornes",
    (1, 0, 0, 0, 1): "Telephone",
    (0, 1, 1, 1, 1): "Quatre",
    (1, 1, 1, 0, 0): "Trois",
}


def nom_du_geste(doigts):
    """Renvoie le nom du geste correspondant au motif, sinon le nombre de doigts."""
    motif = tuple(doigts)
    if motif in GESTES:
        return GESTES[motif]
    return f"{sum(doigts)} doigt(s)"
