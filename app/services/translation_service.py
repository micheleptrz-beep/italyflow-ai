"""
ItalyFlow AI - Translation service with provider abstraction. ASCII only.
Default provider: 'dictionary' (offline, deterministic). Production: swap to OpenAI.
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.i18n import IfGlossaryTerm, IfTranslation


# ---------- Providers ----------
class BaseProvider:
    name = "base"

    def translate(self, text: str, src: str, tgt: str, glossary: dict[str, str]) -> str:
        raise NotImplementedError


class DictionaryProvider(BaseProvider):
    """Offline fallback: applies glossary + tiny built-in dictionary."""
    name = "dictionary"

    BUILTIN = {
        ("it", "en"): {
            "ingredienti": "ingredients", "allergeni": "allergens",
            "peso netto": "net weight", "scadenza": "best before",
            "produttore": "manufacturer", "origine": "origin",
            "olio extravergine di oliva": "extra virgin olive oil",
            "formaggio": "cheese", "vino": "wine",
        },
        ("en", "it"): {
            "ingredients": "ingredienti", "allergens": "allergeni",
            "net weight": "peso netto", "best before": "scadenza",
        },
    }

    def translate(self, text: str, src: str, tgt: str, glossary: dict[str, str]) -> str:
        t = text
        # Glossary first (case-insensitive whole word)
        for k in sorted(glossary.keys(), key=len, reverse=True):
            t = re.sub(rf"\b{re.escape(k)}\b", glossary[k], t, flags=re.IGNORECASE)
        # Built-in fallback
        builtin = self.BUILTIN.get((src, tgt), {})
        for k in sorted(builtin.keys(), key=len, reverse=True):
            t = re.sub(rf"\b{re.escape(k)}\b", builtin[k], t, flags=re.IGNORECASE)
        return t


class OpenAIProvider(BaseProvider):
    """Calls OpenAI if OPENAI_API_KEY is set; otherwise raises so we fall back."""
    name = "openai"

    def translate(self, text: str, src: str, tgt: str, glossary: dict[str, str]) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        from openai import OpenAI  # lazy
        client = OpenAI(api_key=api_key)
        glossary_lines = "\n".join(f"- {k} => {v}" for k, v in glossary.items())
        prompt = (
            f"Translate the following food label text from {src} to {tgt}. "
            f"Be culturally appropriate, not literal. Preserve required label terms. "
            f"Use this glossary strictly:\n{glossary_lines}\n\nTEXT:\n{text}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:32]


class TranslationService:
    def __init__(self, db: Session, provider: Optional[BaseProvider] = None):
        self.db = db
        self.provider = provider or self._default_provider()

    @staticmethod
    def _default_provider() -> BaseProvider:
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider()
        return DictionaryProvider()

    def _glossary(self, user_id: int, src: str, tgt: str) -> dict[str, str]:
        rows = self.db.scalars(
            select(IfGlossaryTerm).where(
                IfGlossaryTerm.user_id == user_id,
                IfGlossaryTerm.src_lang == src,
                IfGlossaryTerm.tgt_lang == tgt,
            )
        )
        return {r.term_src: r.term_tgt for r in rows}

    def translate(self, user_id: int, text: str, src: str, tgt: str,
                  back_check: bool = True) -> dict:
        h = _hash(text)
        cached = self.db.scalar(
            select(IfTranslation).where(
                IfTranslation.user_id == user_id,
                IfTranslation.src_lang == src,
                IfTranslation.tgt_lang == tgt,
                IfTranslation.src_hash == h,
            )
        )
        if cached:
            return {
                "tgt_text": cached.tgt_text,
                "back_translation": cached.back_translation,
                "quality_score": cached.quality_score, "cached": True,
            }
        glossary = self._glossary(user_id, src, tgt)
        try:
            tgt_text = self.provider.translate(text, src, tgt, glossary)
        except Exception:
            tgt_text = DictionaryProvider().translate(text, src, tgt, glossary)
        back = None
        score = 70
        if back_check:
            try:
                back = self.provider.translate(tgt_text, tgt, src, {})
            except Exception:
                back = DictionaryProvider().translate(tgt_text, tgt, src, {})
            score = self._similarity_score(text, back)

        row = IfTranslation(
            user_id=user_id, src_lang=src, tgt_lang=tgt, src_hash=h,
            src_text=text, tgt_text=tgt_text, back_translation=back,
            quality_score=score, glossary_used=list(glossary.keys()),
        )
        self.db.add(row); self.db.commit()
        return {"tgt_text": tgt_text, "back_translation": back,
                "quality_score": score, "cached": False}

    @staticmethod
    def _similarity_score(a: str, b: str) -> int:
        sa = set(re.findall(r"\w+", a.lower()))
        sb = set(re.findall(r"\w+", b.lower()))
        if not sa:
            return 0
        return int(round(100 * len(sa & sb) / len(sa | sb)))
