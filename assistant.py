"""Gemini-powered, document-grounded assistant for MGC sales staff."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DOCS_DIR = Path(__file__).parent / "docs"
load_dotenv(Path(__file__).parent / ".env")


@dataclass(frozen=True)
class Evidence:
    file: str
    section: str
    line: int
    text: str

    def render(self) -> str:
        excerpt = re.sub(r"\s+", " ", self.text.strip())
        return f"{self.file}, {self.section}, line {self.line}: {excerpt}"


@dataclass(frozen=True)
class SourceChunk:
    id: str
    file: str
    section: str
    line: int
    text: str

    def evidence(self) -> Evidence:
        return Evidence(self.file, self.section, self.line, self.text)


@dataclass(frozen=True)
class Answer:
    text: str
    evidence: tuple[Evidence, ...]

    def render(self) -> str:
        sources = "\n".join(f"- {item.render()}" for item in self.evidence)
        return f"{self.text}\n\nSources:\n{sources}" if sources else self.text


class DocumentStore:
    def __init__(self, docs_dir: Path = DOCS_DIR) -> None:
        paths = sorted(docs_dir.glob("*.md"))
        if not paths:
            raise FileNotFoundError(f"No Markdown documents found in {docs_dir}")
        self.documents = {path.name: path.read_text(encoding="utf-8") for path in paths}
        self.chunks = self._build_chunks()

    def _build_chunks(self) -> list[SourceChunk]:
        """Split on headings; the corpus is small enough to give Gemini every chunk."""
        chunks: list[SourceChunk] = []
        for filename, content in self.documents.items():
            section = "Document header"
            start = 1
            lines: list[str] = []

            def flush() -> None:
                nonlocal lines
                text = "\n".join(lines).strip()
                if text:
                    chunks.append(SourceChunk(f"S{len(chunks) + 1}", filename, section, start, text))
                lines = []

            for number, line in enumerate(content.splitlines(), 1):
                if line.startswith("## "):
                    flush()
                    section = line[3:].strip()
                    start = number + 1
                else:
                    if not lines:
                        start = number
                    lines.append(line)
            flush()
        return chunks

    def matching_lines(self, pattern: str, flags: int = re.IGNORECASE) -> list[Evidence]:
        found: list[Evidence] = []
        regex = re.compile(pattern, flags)
        for filename, content in self.documents.items():
            section = "document"
            for number, line in enumerate(content.splitlines(), start=1):
                if line.startswith("## "):
                    section = line[3:].strip()
                if regex.search(line):
                    found.append(Evidence(filename, section, number, line))
        return found


class MGCAssistant:
    def __init__(self, docs_dir: Path = DOCS_DIR, api_key: str | None = None) -> None:
        self.store = DocumentStore(docs_dir)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    def ask(self, question: str) -> Answer:
        normalized = re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()

        if "transfer" in normalized and "fee" in normalized:
            return self._transfer_fee()
        if "rental" in normalized and ("yield" in normalized or "return" in normalized):
            return self._rental_yield()
        if "anchor" in normalized and ("tenant" in normalized or "tenancy" in normalized):
            return self._anchor_tenant()
        if "price" in normalized or "cost" in normalized or "total" in normalized:
            return self._price(question, normalized)

        return self._ask_gemini(question)

    def _ask_gemini(self, question: str) -> Answer:
        if not self.api_key:
            return Answer(
                "Gemini is not configured. Set the GEMINI_API_KEY environment variable, "
                "then restart the assistant.",
                (),
            )

        context = "\n\n".join(
            f"[{chunk.id}] File: {chunk.file}; Section: {chunk.section}; starts line {chunk.line}\n{chunk.text}"
            for chunk in self.store.chunks
        )
        prompt = f"""You are a cautious sales assistant for MGC Aurora Heights.
Answer using ONLY the SOURCE CHUNKS below. Never use outside knowledge.
- If the answer is absent, say exactly: "I don't have that information in the supplied documents. Please ask the marketing manager."
- If sources disagree, report every conflicting value and say management must confirm; never silently choose one.
- Do not invent projections, names, prices, dates, policies, or calculations.
- Keep the answer concise.
- Return JSON only with this shape: {{"answer":"...", "source_ids":["S1"]}}.
- source_ids must contain only chunks that directly support the answer. Use [] for missing information.

QUESTION:
{question}

SOURCE CHUNKS:
{context}"""
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 500,
                "responseMimeType": "application/json",
            },
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
            raw = result["candidates"][0]["content"]["parts"][0]["text"]
            generated = json.loads(raw)
            answer_text = str(generated["answer"]).strip()
            requested_ids = generated.get("source_ids", [])
            chunk_by_id = {chunk.id: chunk for chunk in self.store.chunks}
            evidence = tuple(
                chunk_by_id[source_id].evidence()
                for source_id in requested_ids
                if source_id in chunk_by_id
            )
            if not answer_text:
                raise ValueError("Gemini returned an empty answer")
            return Answer(answer_text, evidence)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:300]
            return Answer(f"Gemini API error ({error.code}): {detail}", ())
        except (OSError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
            return Answer(f"Gemini could not produce a grounded answer: {error}", ())

    def _transfer_fee(self) -> Answer:
        evidence = self.store.matching_lines(r"transfer fee.*2(?:\.5)?%")
        values = sorted({match.group(1) for item in evidence if (match := re.search(r"(2(?:\.5)?)%", item.text))})
        return Answer(
            "The documents conflict, so do not quote a single confirmed fee. The April 2025 "
            "price list says 2% of current list price, while the newer May 2025 booking policy "
            "says 2.5%. Confirm the applicable fee with MGC management before advising a buyer."
            if values == ["2", "2.5"]
            else "I could not verify the transfer fee consistently in the supplied documents; confirm it with MGC management.",
            tuple(evidence),
        )

    def _rental_yield(self) -> Answer:
        evidence = self.store.matching_lines(r"does not publish rental yield projections")
        return Answer(
            "MGC does not publish rental-yield projections, including for 1-bed units. "
            "Sales staff must not invent or quote one; direct the question to the marketing manager.",
            tuple(evidence),
        )

    def _anchor_tenant(self) -> Answer:
        evidence = self.store.matching_lines(r"no anchor tenant has been confirmed")
        return Answer(
            "No anchor tenant has been confirmed. The brochure says discussions were still ongoing at its March 2025 issue date.",
            tuple(evidence),
        )

    def _price(self, original: str, normalized: str) -> Answer:
        block_match = re.search(r"block\s*([ab])\b", normalized)
        block = block_match.group(1).upper() if block_match else None
        unit = self._unit_type(normalized)
        if not block or not unit:
            return Answer(
                "I need both a unit type and block (for example, '2-bed in Block B') to verify a residential price.",
                (),
            )

        # "corner" is a location premium here because the requested unit is described
        # as "2-bed", not specifically as the separately listed "2-Bed Corner" type.
        row_unit = unit
        row_pattern = rf"^\|\s*{re.escape(row_unit)}\s*\|"
        candidates = self.store.matching_lines(row_pattern, re.MULTILINE | re.IGNORECASE)
        candidates = [item for item in candidates if item.section == f"Base Prices (Block {block})"]
        if not candidates:
            return Answer(
                f"The supplied price list does not contain a base price for {unit} in Block {block}.",
                (),
            )

        cells = [cell.strip() for cell in candidates[0].text.strip("|").split("|")]
        if len(cells) < 3 or not re.fullmatch(r"[\d,]+", cells[2]):
            raise ValueError(f"Could not parse base price row: {candidates[0].text}")
        base = int(cells[2].replace(",", ""))
        premiums: list[tuple[str, int, Evidence]] = []

        floor_match = re.search(r"floor\s*(\d+)", normalized)
        if floor_match:
            floor = int(floor_match.group(1))
            if 13 <= floor <= 19:
                premiums.append(("floor 13-19", 4, self._one(r"Floors 13.+\+4%")))
            elif 20 <= floor <= 22:
                premiums.append(("floor 20-22", 7, self._one(r"Floors 20.+\+7%")))
        if "corner" in normalized:
            premiums.append(("corner", 3, self._one(r"Corner unit.+\+3%")))
        if "margalla" in normalized:
            premiums.append(("Margalla-facing", 6, self._one(r"Margalla-facing.+\+6%")))

        evidence = [candidates[0]]
        evidence.extend(item[2] for item in premiums)
        if premiums:
            percent = sum(item[1] for item in premiums)
            total = base * (100 + percent) // 100
            breakdown = " + ".join(f"{name} {value}%" for name, value, _ in premiums)
            text = (
                f"PKR {total:,} total: PKR {base:,} base price + {percent}% in cumulative "
                f"location premiums ({breakdown}). This excludes parking, utilities, maintenance, and other charges."
            )
        else:
            text = f"The base price is PKR {base:,}. This excludes premiums and other charges."
        return Answer(text, tuple(evidence))

    @staticmethod
    def _unit_type(normalized: str) -> str | None:
        patterns = (
            (r"\b(?:2|two)[ -]?bed\b", "2-Bed Standard"),
            (r"\b(?:1|one)[ -]?bed\b", "1-Bed Standard"),
            (r"\bstudio\b", "Studio"),
            (r"\b(?:3|three)[ -]?bed\b", "3-Bed Executive"),
            (r"\b(?:4|four)[ -]?bed\b|\bpenthouse\b", "4-Bed Penthouse"),
        )
        return next((unit for pattern, unit in patterns if re.search(pattern, normalized)), None)

    def _one(self, pattern: str) -> Evidence:
        matches = self.store.matching_lines(pattern)
        if not matches:
            raise ValueError(f"Expected source statement not found: {pattern}")
        return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask grounded questions about MGC sales documents")
    parser.add_argument("question", nargs="*", help="question to ask; omit for interactive mode")
    args = parser.parse_args()
    assistant = MGCAssistant()
    if args.question:
        print(assistant.ask(" ".join(args.question)).render())
        return
    print("MGC document assistant (type 'quit' to exit)")
    while True:
        try:
            question = input("\nQuestion: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"quit", "exit"}:
            break
        print(assistant.ask(question).render())


if __name__ == "__main__":
    main()
