"""Wheatley V2 - a fast, simple voice assistant package.

This package is intentionally flat: one small single-purpose module per concern.
Leaf modules depend only on the standard library and external packages; only
``main.py`` wires the modules together (dependency injection).
"""

from __future__ import annotations

__version__ = "2.0.0"
