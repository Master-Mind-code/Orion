# -*- coding: utf-8 -*-
"""Tests de la base de connaissances évolutive d'Orion.

Les tests d'ingestion travaillent dans un namespace jetable et nettoient
derrière eux : ils ne doivent jamais polluer la mémoire réelle de l'utilisateur.
"""

import io
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from server.memory import knowledge  # noqa: E402
from server.memory import media_ingest  # noqa: E402

TEST_NS = "_test_knowledge"


def _cleanup():
    """Remet le namespace de test à zéro : disque, cache mémoire et journal.

    Effacer le dossier ne suffit pas : rag_tools garde les VectorStore ouverts
    dans un cache, et l'instance survivante continuerait d'écrire vers un
    chemin disparu.
    """
    from server.memory import rag_tools

    rag_tools._stores.pop(TEST_NS, None)
    shutil.rmtree(ROOT / "data" / "memory" / TEST_NS, ignore_errors=True)

    ledger = knowledge._load_ledger()
    ledger["sources"] = [s for s in ledger["sources"] if s.get("namespace") != TEST_NS]
    knowledge.LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    knowledge.LEDGER_FILE.write_text(
        __import__("json").dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════════
# Reconnaissance du type de source
# ════════════════════════════════════════════════════════════════════════════

def test_video_url_detection():
    assert media_ingest.is_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert media_ingest.is_video_url("https://youtu.be/aircAruvnKk")
    assert media_ingest.is_video_url("https://cdn.example.com/cours.mp4")
    assert not media_ingest.is_video_url("https://www.brvm.org/fr/indices")


def test_youtube_id_extraction():
    """Toutes les formes d'URL YouTube doivent donner le même identifiant."""
    for url in ("https://www.youtube.com/watch?v=aircAruvnKk",
                "https://youtu.be/aircAruvnKk",
                "https://www.youtube.com/embed/aircAruvnKk",
                "https://www.youtube.com/shorts/aircAruvnKk",
                "https://m.youtube.com/watch?v=aircAruvnKk&t=42s"):
        assert media_ingest.extract_video_id(url) == "aircAruvnKk", url
    assert media_ingest.extract_video_id("https://example.com/article") is None


def test_source_kind_dispatch():
    """learn_from_source doit reconnaître seul le type de ce qu'on lui donne."""
    manual = ROOT / "MANUEL_MAGISTRAL_CAPACITES_ORION.md"

    extracted = knowledge.extract_source_text(str(manual))
    assert extracted["success"] and extracted["kind"] == "fichier"

    extracted = knowledge.extract_source_text(str(ROOT / "server"))
    assert extracted.get("is_dir") is True

    extracted = knowledge.extract_source_text("Une règle que je veux retenir.")
    assert extracted["success"] and extracted["kind"] == "texte brut"


def test_missing_file_is_treated_as_raw_text():
    """Un chemin inexistant n'est pas une erreur : c'est du texte à retenir.

    Sans ce comportement, « retiens que X » échouerait dès que la phrase
    ressemble vaguement à un chemin.
    """
    extracted = knowledge.extract_source_text("ceci/nexiste/pas mais c'est une note")
    assert extracted["success"] and extracted["kind"] == "texte brut"


# ════════════════════════════════════════════════════════════════════════════
# Ingestion et restitution
# ════════════════════════════════════════════════════════════════════════════

def test_learn_then_recall():
    """Le cœur du cycle : ce qui entre doit pouvoir ressortir."""
    _cleanup()
    try:
        rule = ("Ne jamais risquer plus de 1% du capital sur une seule position. "
                "Le stop loss est placé avant l'entrée, jamais après. ") * 8
        learned = knowledge.learn_from_source(rule, namespace=TEST_NS, tags=["regles"])
        assert learned["success"], learned.get("error")
        assert learned["chunks_added"] >= 1

        taught = knowledge.knowledge_teach("gestion du risque par position",
                                           namespace=TEST_NS)
        assert taught["success"], taught.get("error")
        assert taught["extracts_count"] >= 1
        joined = " ".join(e for m in taught["material"] for e in m["extracts"])
        assert "1%" in joined, "le contenu appris n'est pas retrouvé"
    finally:
        _cleanup()


def test_learning_is_idempotent():
    """Réapprendre sans force dupliquerait les fragments et biaiserait la recherche."""
    _cleanup()
    try:
        manual = str(ROOT / "MANUEL_MAGISTRAL_CAPACITES_ORION.md")
        first = knowledge.learn_from_source(manual, namespace=TEST_NS)
        assert first["success"] and not first.get("already_known")

        second = knowledge.learn_from_source(manual, namespace=TEST_NS)
        assert second.get("already_known") is True, "source réindexée en double"
    finally:
        _cleanup()


def test_too_thin_source_is_rejected():
    """Trois mots n'apprennent rien et polluent les recherches suivantes."""
    _cleanup()
    try:
        result = knowledge.learn_from_source("Note trop courte.", namespace=TEST_NS)
        assert result["success"] is False
        assert "caractères" in result["error"]
    finally:
        _cleanup()


def test_teach_admits_ignorance():
    """Sur un sujet jamais appris, il faut le dire — pas broder."""
    _cleanup()
    try:
        taught = knowledge.knowledge_teach("sujet jamais abordé xyzzy", namespace=TEST_NS)
        assert taught["success"] is False
        assert taught["hint"], "l'utilisateur doit savoir comment y remédier"
    finally:
        _cleanup()


def test_inbox_moves_files_instead_of_deleting():
    """Orion ne doit jamais détruire un document de l'utilisateur."""
    _cleanup()
    knowledge.INBOX_DIR.mkdir(parents=True, exist_ok=True)
    probe = knowledge.INBOX_DIR / "_test_probe.md"
    probe.write_text(("La BRVM cote 47 valeurs réparties en 7 secteurs. "
                      "Le règlement-livraison se fait à J+3. ") * 8, encoding="utf-8")
    moved = knowledge.PROCESSED_DIR / probe.name
    try:
        result = knowledge.learn_from_inbox(namespace=TEST_NS)
        assert result["success"]
        assert not probe.exists(), "le fichier est resté et sera réappris à chaque passage"
        assert moved.exists(), "le fichier a disparu au lieu d'être archivé"
    finally:
        moved.unlink(missing_ok=True)
        probe.unlink(missing_ok=True)
        _cleanup()


def test_status_states_the_limit():
    """Le statut doit rappeler qu'aucun poids de modèle n'est modifié.

    C'est la confusion la plus facile à entretenir sur un système « qui
    apprend » ; le dire explicitement évite de laisser croire à un
    ré-entraînement.
    """
    status = knowledge.knowledge_status()
    assert status["success"]
    assert "poids du modèle ne sont pas" in status["note"]


def test_watcher_starts_and_stops():
    knowledge.start_inbox_watcher(interval_sec=300.0, namespace=TEST_NS)
    assert knowledge.inbox_watcher_status()["active"] is True
    knowledge.stop_inbox_watcher()
    assert knowledge.inbox_watcher_status()["active"] is False


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  OK   {name}")
        except AssertionError as exc:
            failures += 1
            print(f" FAIL  {name}\n       {exc}")
        except Exception as exc:
            failures += 1
            print(f" ERR   {name}\n       {type(exc).__name__}: {exc}")
    print(f"\n{failures} échec(s)" if failures else "\nTous les tests passent.")
