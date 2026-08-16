"""Parse the restaurant knowledge base .md file into rows ready for embedding.

Expected structure (see knowledge_base/issouf_fast_food.md):

    ## Informations pratiques
    - Label : valeur

    ## Horaires d'ouverture
    texte libre

    ## Menu
    ### Emoji Catégorie
    #### Nom du plat
    - id: slug-stable
    - Composition: ...
    - Prix: ...

Internal review notes such as "— **À CONFIRMER** : ..." are stripped from the
text that gets embedded (customers shouldn't see them) but the source .md
file itself is never modified by this parser.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_CONFIRM_MARK = re.compile(r"\s*[—;,-]\s*\*{0,2}[àÀ]\s*confirmer\*{0,2}.*$", re.IGNORECASE)
_BOLD = re.compile(r"\*\*(.*?)\*\*")
_HEADING_EMOJI = re.compile(r"^[^\wÀ-ÿ]+")
_THEMATIC_BREAK = re.compile(r"^-{3,}$")
_PLACEHOLDER = re.compile(r"^à\s*compl[ée]ter$", re.IGNORECASE)


def _clean(text: str) -> str:
    text = _CONFIRM_MARK.sub("", text)
    text = _BOLD.sub(r"\1", text)
    return text.strip()


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "item"


@dataclass
class MenuItem:
    id: str
    name: str
    category: str
    composition: str | None
    price_text: str
    content: str = field(init=False)

    def __post_init__(self) -> None:
        parts = [f"{self.name} ({self.category})"]
        if self.composition:
            parts.append(f"Composition : {self.composition}.")
        parts.append(f"Prix : {self.price_text}.")
        self.content = " ".join(parts)


@dataclass
class InfoFact:
    id: str
    type: str  # "info" | "horaires"
    label: str
    content: str


def parse_knowledge_base(md_text: str) -> tuple[list[MenuItem], list[InfoFact]]:
    section: str | None = None
    current_category = ""
    current_item: dict | None = None

    menu_items: list[MenuItem] = []
    info_facts: list[InfoFact] = []
    horaires_lines: list[str] = []

    def flush_item() -> None:
        nonlocal current_item
        if current_item is None:
            return
        item_id = current_item["id"] or _slugify(f"{current_category}-{current_item['name']}")
        menu_items.append(
            MenuItem(
                id=item_id,
                name=_clean(current_item["name"]),
                category=current_category,
                composition=_clean(current_item["composition"]) if current_item["composition"] else None,
                price_text=_clean(current_item["price_text"] or "prix non communiqué"),
            )
        )
        current_item = None

    for raw_line in md_text.splitlines():
        line = raw_line.strip()

        if line.startswith("## "):
            flush_item()
            heading = line[3:].strip()
            if "Informations pratiques" in heading:
                section = "info"
            elif "Horaires" in heading:
                section = "horaires"
            elif heading == "Menu":
                section = "menu"
            else:
                section = None
            continue

        if section == "menu" and line.startswith("### "):
            flush_item()
            current_category = _HEADING_EMOJI.sub("", line[4:]).strip()
            continue

        if section == "menu" and line.startswith("#### "):
            flush_item()
            current_item = {"name": line[5:].strip(), "id": None, "composition": None, "price_text": None}
            continue

        if section == "menu" and current_item is not None and line.startswith("- "):
            body = line[2:]
            key, _, value = body.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "id":
                current_item["id"] = value
            elif key.startswith("composition"):
                current_item["composition"] = value
            elif key.startswith("prix"):
                current_item["price_text"] = value
            continue

        if section == "info" and line.startswith("- "):
            label, _, value = line[2:].partition(":")
            label = label.strip()
            value = _clean(value.strip())
            if _PLACEHOLDER.match(value):
                continue  # pas encore renseigné : on n'indexe pas un "À COMPLÉTER"
            info_facts.append(
                InfoFact(
                    id=_slugify(label),
                    type="info",
                    label=label,
                    content=f"{label} : {value}",
                )
            )
            continue

        if section == "horaires" and line and not line.startswith((">", "#")) and not _THEMATIC_BREAK.match(line):
            horaires_lines.append(_clean(line))
            continue

    flush_item()

    if horaires_lines:
        info_facts.append(
            InfoFact(
                id="horaires-ouverture",
                type="horaires",
                label="Horaires d'ouverture",
                content=" ".join(horaires_lines),
            )
        )

    return menu_items, info_facts
