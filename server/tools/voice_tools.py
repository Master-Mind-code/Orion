# -*- coding: utf-8 -*-
"""Orion Tools — Voix & Réunions (Dictée Obsidian, Résumé d'appel & réunion)."""

from server.voice.dictation import voice_dictate_obsidian
from server.voice.meeting_summarizer import meeting_summarize

HANDLERS = {
    "voice_dictate_obsidian": lambda p: voice_dictate_obsidian(**p),
    "meeting_summarize":      lambda p: meeting_summarize(**p),
}
