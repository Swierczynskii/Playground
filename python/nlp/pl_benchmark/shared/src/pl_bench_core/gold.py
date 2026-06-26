from __future__ import annotations

from dataclasses import dataclass

from .core import EntitySpan, SentenceSpan

GOLD_SENTENCES = [
    "W dniu 14 lutego 2023 roku funkcjonariusze Wydziału do walki z "
    "Przestępczością Gospodarczą zatrzymali Jana Marka Kowalskiego, "
    "urodzonego 12 marca 1980 roku w Płocku.",
    "Podejrzany, legitymujący się dowodem osobistym o numerze ARY 654321 "
    "oraz numerem PESEL 80031205512, jest oskarżony o fałszowanie "
    "dokumentacji kredytowej.",
    "Zatrzymania dokonano w miejscu zamieszkania podejrzanego, tj. w "
    "Warszawie przy ulicy Złotej 44 m. 12.",
    "Podczas przeszukania lokalu zabezpieczono laptopa marki Dell oraz "
    "telefon komórkowy powiązany z numerem +48 601-234-567, "
    "zarejestrowanym na jego żonę, Annę Kowalską.",
    "Jan Kowalski przyznał się do wyłudzenia kwoty 50 000 PLN na szkodę "
    "banku PKO BP.",
]

GOLD_ENTITIES = [
    ("14 lutego 2023 roku", 1, "DATE"),
    ("Jana Marka Kowalskiego", 1, "PERSON"),
    ("12 marca 1980 roku", 1, "DATE"),
    ("Płocku", 1, "LOC"),
    ("Warszawie", 1, "LOC"),
    ("Annę Kowalską", 1, "PERSON"),
    ("Jan Kowalski", 1, "PERSON"),
    ("50 000 PLN", 1, "MONEY"),
    ("PKO BP", 1, "ORG"),
]


@dataclass
class LemmaProbe:
    text: str
    occurrence: int
    expected_lemma: str
    # Coarse Universal POS tag. Comparison normalises every pipeline to UPOS so the
    # SGJP/NKJP tagset (Morfeusz) and the UD tagsets (spaCy, Stanza) are comparable.
    expected_upos: str = ""


@dataclass
class GoldReference:
    sentences: list[SentenceSpan]
    lemma_probes: list[LemmaProbe]
    entities: list[EntitySpan]


LEMMA_PROBES = [
    LemmaProbe("dniu", 1, "dzień", "NOUN"),
    LemmaProbe("funkcjonariusze", 1, "funkcjonariusz", "NOUN"),
    LemmaProbe("zatrzymali", 1, "zatrzymać", "VERB"),
    LemmaProbe("Podejrzany", 1, "podejrzany", "ADJ"),
    LemmaProbe("numerem", 1, "numer", "NOUN"),
    LemmaProbe("Zatrzymania", 1, "zatrzymanie", "NOUN"),
    LemmaProbe("miejscu", 1, "miejsce", "NOUN"),
    LemmaProbe("mieszkania", 1, "mieszkanie", "NOUN"),
    LemmaProbe("przeszukania", 1, "przeszukanie", "NOUN"),
    LemmaProbe("zabezpieczono", 1, "zabezpieczyć", "VERB"),
    LemmaProbe("żonę", 1, "żona", "NOUN"),
    LemmaProbe("przyznał", 1, "przyznać", "VERB"),
    LemmaProbe("wyłudzenia", 1, "wyłudzenie", "NOUN"),
    LemmaProbe("kwoty", 1, "kwota", "NOUN"),
    LemmaProbe("banku", 1, "bank", "NOUN"),
]


def _find_nth_span(text: str, needle: str, occurrence: int) -> tuple[int, int]:
    start = -1
    search_from = 0
    for _ in range(occurrence):
        start = text.find(needle, search_from)
        if start == -1:
            raise ValueError(f"Could not find occurrence {occurrence} of {needle!r}.")
        search_from = start + len(needle)
    return start, start + len(needle)


def _resolve_sentences(text: str) -> list[SentenceSpan]:
    spans: list[SentenceSpan] = []
    search_from = 0
    for sentence in GOLD_SENTENCES:
        start = text.find(sentence, search_from)
        if start == -1:
            raise ValueError(f"Could not resolve sentence: {sentence!r}")
        end = start + len(sentence)
        spans.append(SentenceSpan(start=start, end=end, text=sentence))
        search_from = end
    return spans


def _resolve_entities(text: str) -> list[EntitySpan]:
    entities: list[EntitySpan] = []
    for needle, occurrence, label in GOLD_ENTITIES:
        start, end = _find_nth_span(text, needle, occurrence)
        entities.append(EntitySpan(start=start, end=end, label=label, text=needle))
    return entities


def build_gold_reference(text: str) -> GoldReference:
    return GoldReference(
        sentences=_resolve_sentences(text),
        lemma_probes=LEMMA_PROBES,
        entities=_resolve_entities(text),
    )
