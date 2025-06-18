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

def _load_config():
    """Load YAML config from fixed path inside the repo."""
    cfg_path = os.path.join("Wheatley", "python", "src", "config", "config.yaml")
    print(f"Loading config from {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass
class Config:
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1"))
    temperature: float = 0.3
    # Only Python and Arduino files now
    file_types: List[str] = field(default_factory=lambda: [".py", ".ino"])


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------
class LLMClient:
    """Thin wrapper around the OpenAI *Responses* API."""

    def __init__(self, cfg: Config):
        raw = _load_config()
        self.client = OpenAI(api_key=raw["secrets"]["openai_api_key"])
        self.model = cfg.model
        self.temperature = cfg.temperature

    # ------------------------------------------------------------------
    def summarise(self, content: str, filename: str, *, dry_run: bool = False):
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
    def _instructions_for(filename: str):
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
    def _extract_text(resp: Any):
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

    def crawl(self):
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
        if self.verbose:
            print(f"[INFO] Summariser initialized with dry_run={self.dry_run}, verbose={self.verbose}")

    def run(self, target: str | Path):
        target_path = Path(target).resolve()
        if self.verbose:
            print(f"[INFO] Target path resolved to: {target_path}")
        files = DirectoryCrawler(target_path, self.cfg.file_types).crawl()
        if self.verbose:
            print(f"[INFO] Found {len(files)} files to summarise.")

        bar = tqdm(files, desc="Summarising", disable=not self.verbose)
        by_dir: Dict[Path, List[str]] = {}

        for file in bar:
            if self.verbose:
                bar.set_description(str(file))
                print(f"[INFO] Summarising file: {file}")
            text = file.read_text(encoding="utf-8", errors="ignore")
            summary = self.llm.summarise(text, str(file), dry_run=self.dry_run)
            by_dir.setdefault(file.parent, []).append(f"### {file}\n{summary}\n")
            if self.verbose:
                print(f"[INFO] Summary for {file} complete.")

        if self.verbose:
            print("[INFO] Writing folder-level AI summaries...")
        self._write_folder_md(by_dir)
        if self.verbose:
            print("[INFO] Writing root-level AI overview...")
        overview = self._write_root_md(target_path, by_dir)
        if self.verbose:
            print("[INFO] Writing Mermaid graph of codebase structure for each directory...")
        self._write_graph_md_per_directory(by_dir)
        if self.verbose:
            print("[INFO] Writing root-level Mermaid overview...")
        self._write_root_mermaid_overview(target_path, files)
        if self.verbose:
            print("[INFO] Summarisation process complete.")
        return overview

    # ------------------------------------------------------------------
    @staticmethod
    def _write_folder_md(groups: Dict[Path, List[str]]):
        for folder, snippets in groups.items():
            print(f"[INFO] Writing README_AI.md for folder: {folder}")
            (folder / "README_AI.md").write_text("# AI Summary\n\n" + "\n".join(snippets), encoding="utf-8")

    def _write_root_md(self, root: Path, groups: Dict[Path, List[str]]):
        print(f"[INFO] Generating root-level summary at: {root / 'README_AI.md'}")
        combined = "\n".join(item for group in groups.values() for item in group)
        overview = self.llm.summarise(combined, "global_summary", dry_run=self.dry_run)
        (root / "README_AI.md").write_text("# AI Codebase Overview\n\n" + overview, encoding="utf-8")
        print(f"[INFO] Root-level summary written.")
        return overview

    def _write_graph_md_per_directory(self, by_dir: Dict[Path, List[str]]):
        """
        For each directory, generate a Mermaid diagram of the files in that directory and write it to AI_Graph.md.
        """
        for folder in by_dir:
            print(f"[INFO] Generating Mermaid diagram for directory: {folder}")
            files = [f for f in folder.iterdir() if f.is_file() and f.suffix in self.cfg.file_types]
            file_contexts = []
            for file in files:
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    content = ""
                file_contexts.append(
                    f"File: {file.name}\nContent:\n{content}\n---"
                )
            context_str = "\n".join(file_contexts)

            prompt = (
                "Given the following files in this directory and their contents, generate a Mermaid diagram "
                "that visualizes the structure as a graph. Each file should be a node. "
                "If you can infer relationships between files (such as imports, class usage, or function calls), "
                "show those as edges as well. Use the 'graph TD' format. "
                "Only output the Mermaid code block (including the opening and closing ```mermaid lines).\n\n"
                f"{context_str}"
            )

            mermaid_diagram = self.llm.summarise(prompt, "AI_Graph.md", dry_run=self.dry_run)
            (folder / "AI_Graph.md").write_text(f"# AI Directory Structure\n\n{mermaid_diagram.strip()}\n", encoding="utf-8")
            print(f"[INFO] Mermaid diagram written to: {folder / 'AI_Graph.md'}")

    def _write_root_mermaid_overview(self, root: Path, files: list[Path]):
        """
        Generate a Mermaid diagram for the entire codebase, focusing on code-level mapping:
        nodes represent main classes, functions, or logical components (not just files),
        and edges show their relationships and interactions. The LLM's output is written
        directly to AI_Graph.md in the root.
        """
        if self.verbose:
            print(f"[INFO] Generating root-level Mermaid overview at: {root / 'AI_Graph.md'}")
        file_contexts = []
        for file in files:
            try:
                content = file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""
            file_contexts.append(
                f"File: {file.name}\nContent:\n{content}\n---"
            )
        context_str = "\n".join(file_contexts)

        prompt = (
            "You are to write a Mermaid diagram that maps the codebase at the code logic level. "
            "STRICTLY FOLLOW Mermaid syntax: "
            "1. Begin with a YAML metadata block for diagram configuration (e.g., layout: dagre, look: classic, theme: neutral). "
            "2. Immediately follow with the diagram type declaration (e.g., flowchart TD). "
            "3. For each main class, function, or logical component in the codebase, create a node with its name and a concise description of its role. "
            "4. Draw edges to represent code-level relationships and interactions (such as function calls, class usage, inheritance, or data flow). "
            "5. Focus on mapping the logic and structure of the code, not just file-to-file interactions. "
            "6. Output ONLY a valid Mermaid code block, including the opening and closing ```mermaid lines. "
            "7. Do NOT include any prose, explanation, or extra text. "
            "8. Use best practices for Mermaid syntax and configuration. "
            "9. Avoid diagram-breaking words or symbols. "
            "10. See https://mermaid.js.org/syntax/flowchart.html for syntax reference. "
            "\n\n"
            "Example:\n"
            "```mermaid\n"
            "---\n"
            "config:\n"
            "  layout: dagre\n"
            "  look: classic\n"
            "  theme: neutral\n"
            "---\n"
            "flowchart TD\n"
            "  Summariser[Summariser: Orchestrates summarization process]\n"
            "  LLMClient[LLMClient: Handles LLM API calls]\n"
            "  DirectoryCrawler[DirectoryCrawler: Finds files to summarize]\n"
            "  Summariser --> LLMClient\n"
            "  Summariser --> DirectoryCrawler\n"
            "```\n"
            "\nNow, for the following files and their contents, generate the diagram:\n"
            f"{context_str}"
        )

        mermaid_diagram = self.llm.summarise(prompt, "AI_Graph.md", dry_run=self.dry_run)
        (root / "AI_Graph.md").write_text(f"{mermaid_diagram.strip()}\n", encoding="utf-8")
        if self.verbose:
            print(f"[INFO] Root-level Mermaid overview written to: {root / 'AI_Graph.md'}")


# ---------------------------------------------------------------------------
# CLI entry‑point
# ---------------------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(description="Generate LLM‑based code summaries.")
    p.add_argument("--path", "-p", default=".", help="Directory to analyse.")
    p.add_argument("--dry-run", action="store_true", help="Run without calling the API.")
    return p.parse_args()


def main():
    args = _parse_args()
    Summariser(Config(), dry_run=args.dry_run, verbose=True).run(args.path)


if __name__ == "__main__":
    main()
