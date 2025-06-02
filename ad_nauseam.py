#!/usr/bin/env python3
"""llm_code_summarizer.py

Generates AI summaries for **Python (.py)** and **Arduino (.ino)** source files
while skipping virtual‑env directories. It uses the OpenAI v1.x *Responses* API
via the official `openai.OpenAI` client.
"""
from __future__ import annotations

import os
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Dict, Any

import yaml
from openai import OpenAI  # Official client
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load YAML config from fixed path inside the repo."""
    cfg_path = os.path.join("Wheatly", "python", "src", "config", "config.yaml")
    print(f"Loading config from {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass
class Config:
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o"))
    temperature: float = 0.3
    # Only Python and Arduino files now
    file_types: List[str] = field(default_factory=lambda: [".py", ".ino"])


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------
class LLMClient:
    """Thin wrapper around the OpenAI *Responses* API."""

    def __init__(self, cfg: Config) -> None:
        raw = _load_config()
        self.client = OpenAI(api_key=raw["secrets"]["openai_api_key"])
        self.model = cfg.model
        self.temperature = cfg.temperature

    # ------------------------------------------------------------------
    def summarise(self, content: str, filename: str, *, dry_run: bool = False) -> str:
        instructions = self._instructions_for(filename)
        if dry_run:
            return f"[DRY‑RUN] {filename}:\n{instructions}"

        completion = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=content,
            temperature=self.temperature,
        )
        return self._extract_text(completion)

    # ------------------------------------------------------------------
    @staticmethod
    def _instructions_for(filename: str) -> str:
        """Return detailed instructions tailored to file type for in-depth summaries."""
        base = os.path.basename(filename)
        if base.endswith(".ino"):
            return (
                "Provide a detailed summary of this Arduino (.ino) sketch in plain English. "
                "Describe the overall purpose, main functions, and how hardware peripherals are used. "
                "List and explain the key classes, functions, and their responsibilities. "
                "Describe the structure of the code, how components interact, and any notable algorithms or logic. "
                "Mention any external libraries or dependencies, and highlight configuration or environment requirements."
            )
        return (
            "Provide a detailed summary of the following Python script. "
            "Describe its overall purpose, main classes and functions, and their responsibilities. "
            "Explain the structure of the code and how its components interact. "
            "Highlight any external dependencies, APIs, or configuration requirements. "
            "Describe any notable algorithms or logic, and their purpose. "
            "Avoid code snippets, but be thorough in your explanation."
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_text(resp: Any) -> str:
        """Handle several possible SDK response shapes."""
        if hasattr(resp, "output_text") and isinstance(resp.output_text, str):
            return resp.output_text.strip()
        if hasattr(resp, "output"):
            itm = resp.output[0]
            for field in ("text", "content"):
                if hasattr(itm, field):
                    val = getattr(itm, field)
                    if isinstance(val, str):
                        return val.strip()
        if hasattr(resp, "choices"):
            return resp.choices[0].message.content.strip()
        raise RuntimeError("Unexpected OpenAI response schema; cannot extract text.")


# ---------------------------------------------------------------------------
# File crawler
# ---------------------------------------------------------------------------
class DirectoryCrawler:
    """Yield .py and .ino files under *root*, excluding **.venv** folders."""

    def __init__(self, root: str | Path, extensions: Iterable[str]):
        self.root = Path(root).resolve()
        self.extensions = tuple(extensions)

    def crawl(self) -> List[Path]:
        """Return matching files, skipping any path within a .venv directory."""
        return [
            p
            for p in self.root.rglob("*")
            if (
                p.is_file()
                and p.suffix in self.extensions
                and ".venv" not in p.parts
            )
        ]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class Summariser:
    def __init__(self, cfg: Config, *, dry_run: bool = False, verbose: bool = False):
        self.llm = LLMClient(cfg)
        self.dry_run = dry_run
        self.verbose = verbose
        self.cfg = cfg

    def run(self, target: str | Path) -> str:
        target_path = Path(target).resolve()
        files = DirectoryCrawler(target_path, self.cfg.file_types).crawl()

        bar = tqdm(files, desc="Summarising", disable=not self.verbose)
        by_dir: Dict[Path, List[str]] = {}

        for file in bar:
            if self.verbose:
                bar.set_description(str(file))
            text = file.read_text(encoding="utf-8", errors="ignore")
            summary = self.llm.summarise(text, str(file), dry_run=self.dry_run)
            by_dir.setdefault(file.parent, []).append(f"### {file}\n{summary}\n")

        self._write_folder_md(by_dir)
        return self._write_root_md(target_path, by_dir)

    # ------------------------------------------------------------------
    @staticmethod
    def _write_folder_md(groups: Dict[Path, List[str]]):
        for folder, snippets in groups.items():
            (folder / "README_AI.md").write_text("# AI Summary\n\n" + "\n".join(snippets), encoding="utf-8")

    def _write_root_md(self, root: Path, groups: Dict[Path, List[str]]) -> str:
        combined = "\n".join(item for group in groups.values() for item in group)
        overview = self.llm.summarise(combined, "global_summary", dry_run=self.dry_run)
        (root / "README_AI.md").write_text("# AI Codebase Overview\n\n" + overview, encoding="utf-8")
        return overview


# ---------------------------------------------------------------------------
# CLI entry‑point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate LLM‑based code summaries.")
    p.add_argument("--path", "-p", default=".", help="Directory to analyse.")
    p.add_argument("--dry-run", action="store_true", help="Run without calling the API.")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    Summariser(Config(), dry_run=args.dry_run, verbose=True).run(args.path)


if __name__ == "__main__":
    main()
