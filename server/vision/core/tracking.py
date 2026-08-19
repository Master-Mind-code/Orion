# -*- coding: utf-8 -*-
"""Suivi d'objets (tracking) léger et compteur de franchissement de ligne.

Tracker par association IoU (greedy) — n'utilise que numpy, aucune dépendance
lourde (pas de torch). Suffisant pour compter des personnes/véhicules qui
franchissent une ligne virtuelle quand la détection tourne à quelques FPS.
"""


def _iou(a, b):
    """Intersection-over-Union de deux boîtes (x1, y1, x2, y2)."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    aire_a = (ax2 - ax1) * (ay2 - ay1)
    aire_b = (bx2 - bx1) * (by2 - by1)
    return inter / (aire_a + aire_b - inter)


def _centre(b):
    return ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)


class Tracker:
    """Attribue un identifiant stable à chaque objet d'une image à l'autre."""

    def __init__(self, iou_min=0.3, max_perdu=15):
        self.iou_min = iou_min
        self.max_perdu = max_perdu     # images tolérées sans revoir l'objet
        self.tracks = {}               # id -> {bbox, centroid, perdu}
        self._prochain_id = 1

    def update(self, boxes):
        """Met à jour les pistes avec les boîtes détectées.

        `boxes` : liste de (x1, y1, x2, y2).
        Renvoie la liste (id, bbox, centroid) des pistes vues cette image.
        """
        ids = list(self.tracks)

        # Toutes les paires (IoU, id_piste, index_detection), triées décroissant.
        paires = []
        for ti in ids:
            for di, b in enumerate(boxes):
                paires.append((_iou(self.tracks[ti]["bbox"], b), ti, di))
        paires.sort(reverse=True)

        pistes_assignees, det_assignees = set(), set()
        for iou, ti, di in paires:
            if iou < self.iou_min:
                break
            if ti in pistes_assignees or di in det_assignees:
                continue
            pistes_assignees.add(ti)
            det_assignees.add(di)
            b = boxes[di]
            self.tracks[ti].update(bbox=b, centroid=_centre(b), perdu=0)

        # Détections non assignées -> nouvelles pistes.
        for di, b in enumerate(boxes):
            if di in det_assignees:
                continue
            self.tracks[self._prochain_id] = {"bbox": b, "centroid": _centre(b), "perdu": 0}
            self._prochain_id += 1

        # Vieillissement des pistes non revues.
        for ti in ids:
            if ti not in pistes_assignees:
                self.tracks[ti]["perdu"] += 1
        self.tracks = {ti: t for ti, t in self.tracks.items()
                       if t["perdu"] <= self.max_perdu}

        return [(ti, t["bbox"], t["centroid"])
                for ti, t in self.tracks.items() if t["perdu"] == 0]


class CompteurLigne:
    """Compte les objets qui franchissent une ligne virtuelle, par sens."""

    def __init__(self, p1, p2):
        self.p1, self.p2 = p1, p2
        self.sens_a = 0            # franchissements dans un sens
        self.sens_b = 0            # franchissements dans l'autre sens
        self._cote = {}           # id -> dernier côté connu (+1 / -1)

    def _cote_de(self, point):
        (x1, y1), (x2, y2) = self.p1, self.p2
        d = (x2 - x1) * (point[1] - y1) - (y2 - y1) * (point[0] - x1)
        return 1 if d > 0 else (-1 if d < 0 else 0)

    def maj(self, track_id, centroid):
        """Renvoie 'a', 'b' si franchissement, sinon None."""
        cote = self._cote_de(centroid)
        if cote == 0:
            return None
        precedent = self._cote.get(track_id)
        self._cote[track_id] = cote
        if precedent is not None and precedent != cote:
            if cote > 0:
                self.sens_a += 1
                return "a"
            self.sens_b += 1
            return "b"
        return None

    def reset(self):
        self.sens_a = 0
        self.sens_b = 0
        self._cote.clear()
