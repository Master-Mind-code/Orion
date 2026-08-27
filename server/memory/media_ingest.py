"""
Extraction du contenu textuel des médias — vidéos et audio.

Deux voies, de la moins chère à la plus coûteuse :

  1. Sous-titres publiés (youtube-transcript-api). Aucun téléchargement, une
     seconde environ. Couvre la grande majorité des vidéos YouTube, y compris
     les sous-titres auto-générés.
  2. Transcription de l'audio (yt-dlp + faster-whisper). Fonctionne sur
     n'importe quelle vidéo ou fichier audio, mais télécharge la piste et fait
     tourner Whisper : compter plusieurs minutes par vidéo.

La voie 2 exige **ffmpeg**, un binaire système que pip n'installe pas. En son
absence, l'erreur retournée le dit explicitement plutôt que de laisser tomber
une exception de décodage incompréhensible.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Durée d'audio au-delà de laquelle la transcription devient déraisonnable
# sur CPU : trois heures de vidéo occuperaient la machine une heure durant.
MAX_AUDIO_MINUTES = 90

_YOUTUBE_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com",
                  "youtu.be", "music.youtube.com")

_YOUTUBE_ID_PATTERNS = (
    r"(?:v=|/videos/|/embed/|/shorts/|/live/|youtu\.be/)([A-Za-z0-9_-]{11})",
)

DEFAULT_LANGUAGES = ("fr", "fr-FR", "en", "en-US", "en-GB")


def is_video_url(url: str) -> bool:
    """Vrai si l'URL désigne une vidéo qu'on sait traiter."""
    lowered = url.lower()
    if any(host in lowered for host in _YOUTUBE_HOSTS):
        return True
    return lowered.split("?")[0].endswith(
        (".mp4", ".mkv", ".webm", ".mov", ".avi", ".mp3", ".m4a", ".wav", ".ogg", ".flac")
    )


def extract_video_id(url: str) -> Optional[str]:
    """Identifiant YouTube contenu dans une URL, quelle que soit sa forme."""
    for pattern in _YOUTUBE_ID_PATTERNS:
        found = re.search(pattern, url)
        if found:
            return found.group(1)
    # URL réduite à l'identifiant nu
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()
    return None


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


# ════════════════════════════════════════════════════════════════════════════
# Voie 1 — sous-titres publiés
# ════════════════════════════════════════════════════════════════════════════

def fetch_captions(video_id: str,
                   languages: tuple = DEFAULT_LANGUAGES) -> Dict[str, Any]:
    """Sous-titres d'une vidéo YouTube.

    On tente d'abord les langues demandées, puis n'importe quelle piste
    disponible, quitte à la faire traduire par YouTube : une vidéo en espagnol
    reste exploitable.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return {"success": False, "error": (
            "youtube-transcript-api n'est pas installé. Installe avec :\n"
            "    pip install -r requirements-learning.txt")}

    api = YouTubeTranscriptApi()

    try:
        fetched = api.fetch(video_id, languages=list(languages))
        used_language = getattr(fetched, "language_code", "?")
    except Exception:
        # Aucune des langues demandées : on prend ce qui existe.
        try:
            available = api.list(video_id)
            transcript = next(iter(available))
            if transcript.is_translatable:
                for target in ("fr", "en"):
                    if any(t.language_code == target for t in transcript.translation_languages):
                        transcript = transcript.translate(target)
                        break
            fetched = transcript.fetch()
            used_language = transcript.language_code
        except Exception as exc:
            return {"success": False, "error":
                    f"Aucun sous-titre exploitable : {type(exc).__name__}: {exc}"[:250]}

    segments = [
        {"start": round(float(s.start), 2), "text": s.text.strip()}
        for s in fetched if s.text and s.text.strip()
    ]
    if not segments:
        return {"success": False, "error": "Sous-titres vides."}

    return {
        "success": True,
        "method": "sous-titres",
        "language": used_language,
        "text": " ".join(s["text"] for s in segments),
        "segments_count": len(segments),
        "duration_seconds": round(segments[-1]["start"], 1),
    }


# ════════════════════════════════════════════════════════════════════════════
# Voie 2 — transcription de l'audio
# ════════════════════════════════════════════════════════════════════════════

def _download_audio(url: str, target_dir: Path,
                    cookies_from_browser: Optional[str] = None,
                    cookies_file: Optional[str] = None) -> Dict[str, Any]:
    """Télécharge la meilleure piste audio d'une URL via yt-dlp.

    YouTube refuse l'accès anonyme depuis beaucoup d'adresses IP et réclame une
    session authentifiée. Deux façons de la fournir, toutes deux désactivées par
    défaut — donner accès à sa session n'est pas anodin :

    `cookies_from_browser` ('firefox', 'chrome', 'edge'...) laisse yt-dlp lire
    directement la base de cookies du navigateur. Échoue souvent sous Windows :
    la base est verrouillée si le navigateur tourne, et depuis Chromium 127 les
    cookies sont chiffrés par liaison applicative (« Failed to decrypt with
    DPAPI »), ce que yt-dlp ne sait pas déchiffrer sur Chrome, Edge et Brave.

    `cookies_file` pointe un export au format Netscape (cookies.txt), obtenu via
    une extension de navigateur. Plus manuel, mais insensible aux deux
    problèmes ci-dessus et sous le contrôle de l'utilisateur, qui choisit ce
    qu'il exporte.
    """
    try:
        import yt_dlp
    except ImportError:
        return {"success": False, "error": (
            "yt-dlp n'est pas installé. Installe avec :\n"
            "    pip install -r requirements-learning.txt")}

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(target_dir / "audio.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    if cookies_file:
        options["cookiefile"] = str(Path(cookies_file).expanduser())
    elif cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as exc:
        return {"success": False, "error": f"Téléchargement impossible : {exc}"[:250]}

    duration = float(info.get("duration") or 0)
    if duration > MAX_AUDIO_MINUTES * 60:
        return {"success": False, "error": (
            f"Vidéo de {duration / 60:.0f} minutes : au-delà de la limite de "
            f"{MAX_AUDIO_MINUTES} minutes. Transcrire prendrait des heures sur CPU.")}

    downloaded = sorted(target_dir.glob("audio.*"))
    if not downloaded:
        return {"success": False, "error": "Aucun fichier audio récupéré."}

    return {
        "success": True,
        "path": downloaded[0],
        "title": info.get("title", ""),
        "duration_seconds": round(duration, 1),
        "uploader": info.get("uploader", ""),
    }


def transcribe_audio_file(path: Path, language: Optional[str] = None) -> Dict[str, Any]:
    """Transcrit un fichier audio local avec le Whisper déjà embarqué."""
    if not has_ffmpeg():
        return {"success": False, "error": (
            "ffmpeg est introuvable dans le PATH. Whisper en a besoin pour décoder "
            "l'audio. Installe-le puis relance : winget install Gyan.FFmpeg")}

    try:
        from server.transcribe import _get_model
    except ImportError as exc:
        return {"success": False, "error": f"Whisper indisponible : {exc}"}

    try:
        model = _get_model()
        segments, info = model.transcribe(
            str(path),
            language=language,
            beam_size=5,
            temperature=0.0,
            condition_on_previous_text=False,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as exc:
        return {"success": False, "error": f"Transcription échouée : {type(exc).__name__}: {exc}"[:250]}

    if not text:
        return {"success": False, "error": "Transcription vide : aucune parole détectée."}

    return {
        "success": True,
        "method": "transcription Whisper",
        "language": getattr(info, "language", language or "?"),
        "text": text,
    }


def transcribe_from_url(url: str, language: Optional[str] = None,
                        cookies_from_browser: Optional[str] = None,
                        cookies_file: Optional[str] = None) -> Dict[str, Any]:
    """Télécharge l'audio d'une URL puis le transcrit. Nettoie derrière lui."""
    with tempfile.TemporaryDirectory(prefix="orion_media_") as tmp:
        downloaded = _download_audio(url, Path(tmp),
                                     cookies_from_browser=cookies_from_browser,
                                     cookies_file=cookies_file)
        if not downloaded["success"]:
            return downloaded

        result = transcribe_audio_file(downloaded["path"], language=language)
        if result["success"]:
            result["title"] = downloaded.get("title", "")
            result["uploader"] = downloaded.get("uploader", "")
            result["duration_seconds"] = downloaded.get("duration_seconds")
        return result


# ════════════════════════════════════════════════════════════════════════════
# Point d'entrée
# ════════════════════════════════════════════════════════════════════════════

def get_video_transcript(url: str, language: Optional[str] = None,
                         allow_audio_fallback: bool = True,
                         cookies_from_browser: Optional[str] = None,
                         cookies_file: Optional[str] = None) -> Dict[str, Any]:
    """Contenu textuel d'une vidéo, par la voie la moins coûteuse disponible.

    Les sous-titres d'abord — une seconde contre plusieurs minutes — et le
    téléchargement plus transcription seulement s'ils font défaut.
    """
    video_id = extract_video_id(url)

    if video_id:
        languages = (language, *DEFAULT_LANGUAGES) if language else DEFAULT_LANGUAGES
        captions = fetch_captions(video_id, languages=tuple(dict.fromkeys(filter(None, languages))))
        if captions["success"]:
            captions["url"] = url
            captions["video_id"] = video_id
            return captions
        caption_error = captions["error"]
    else:
        caption_error = "URL non reconnue comme une vidéo YouTube."

    if not allow_audio_fallback:
        return {"success": False, "error": caption_error,
                "hint": "Réessaie avec allow_audio_fallback pour transcrire l'audio."}

    fallback = transcribe_from_url(url, language=language,
                                   cookies_from_browser=cookies_from_browser,
                                   cookies_file=cookies_file)
    if fallback["success"]:
        fallback["url"] = url
        fallback["captions_note"] = f"Sous-titres indisponibles ({caption_error[:80]})"
    else:
        fallback["error"] = (
            f"Sous-titres : {caption_error[:120]} | "
            f"Audio : {fallback.get('error', '')[:120]}"
        )
        error_text = fallback["error"].lower()
        if "bot" in error_text or "IpBlocked" in caption_error:
            fallback["hint"] = (
                "YouTube refuse l'accès anonyme depuis cette adresse IP. Il faut lui "
                "fournir une session authentifiée : cookies_from_browser='firefox', ou "
                "cookies_file pointant un export cookies.txt."
            )
        if "dpapi" in error_text or "could not copy" in error_text:
            fallback["hint"] = (
                "Les cookies du navigateur sont inaccessibles : base verrouillée si le "
                "navigateur tourne, et depuis Chromium 127 Chrome/Edge/Brave chiffrent "
                "leurs cookies d'une façon que yt-dlp ne sait pas déchiffrer. Exporte un "
                "cookies.txt avec une extension de navigateur et passe-le en cookies_file."
            )
    return fallback
