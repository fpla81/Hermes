"""Anonimização de PII em textos antes de chamar LLM.

Cobre o que dá pra fazer com regex de forma estável:
CPF, CNPJ, OAB, telefone, e-mail. Nomes próprios e endereços ficam para
uma fase futura (precisa de NER ou heurísticas calibradas para textos do TST).

O processo é reversível: ``anonymize`` devolve o texto sanitizado + um
mapa ``{placeholder: original}``. ``deanonymize`` reverte usando o mapa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar

CPF_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
CNPJ_RE = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
OAB_RE = re.compile(r"\bOAB\s*/?\s*[A-Z]{2}\s*\d{2,6}\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"\b(?:\+?55\s*)?\(?\d{2}\)?\s*9?\d{4}-?\d{4}\b"
)


@dataclass
class AnonymizationResult:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)

    PATTERNS: ClassVar[list[tuple[str, re.Pattern[str]]]] = [
        ("CPF", CPF_RE),
        ("CNPJ", CNPJ_RE),
        ("OAB", OAB_RE),
        ("EMAIL", EMAIL_RE),
        ("PHONE", PHONE_RE),
    ]


def anonymize(text: str) -> AnonymizationResult:
    mapping: dict[str, str] = {}
    counters: dict[str, int] = {}

    out = text
    for label, pattern in AnonymizationResult.PATTERNS:
        def replace(match: re.Match[str], _label: str = label) -> str:
            original = match.group(0)
            counters[_label] = counters.get(_label, 0) + 1
            placeholder = f"<{_label}_{counters[_label]}>"
            mapping[placeholder] = original
            return placeholder

        out = pattern.sub(replace, out)

    return AnonymizationResult(text=out, mapping=mapping)


def deanonymize(text: str, mapping: dict[str, str]) -> str:
    out = text
    for placeholder, original in mapping.items():
        out = out.replace(placeholder, original)
    return out
