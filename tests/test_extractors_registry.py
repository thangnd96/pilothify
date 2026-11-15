"""Facade / registry identity guards for the per-language extractor split.

The ``extract.py`` decomposition moved each language extractor into its
own ``pilothify/extractors/<lang>.py`` module, kept a verbatim re-export in
``pilothify.extract`` (the facade every existing importer uses), and seeded a
``pilothify.extractors.LANGUAGE_EXTRACTORS`` registry. Three things must stay
true for that split to be behavior-preserving:

- the function is importable from its new per-language module,
- ``pilothify.extract`` still re-exports the SAME function object (facade
  identity — a stale copy or shadowing import would silently diverge),
- ``LANGUAGE_EXTRACTORS`` maps to that same object (registry identity).

Originally proposed by @Cekaru as a per-language check; generalized
here to sweep the whole registry so a future move that forgets the facade
re-export (or re-exports a different object) fails loudly.
"""
from __future__ import annotations

import pilothify.extract as facade
from pilothify.extractors import LANGUAGE_EXTRACTORS


def test_every_registry_extractor_is_reexported_from_facade():
    missing = []
    diverged = []
    for lang, fn in LANGUAGE_EXTRACTORS.items():
        name = getattr(fn, "__name__", None)
        if not name or not hasattr(facade, name):
            missing.append((lang, name))
            continue
        if getattr(facade, name) is not fn:
            diverged.append((lang, name))
    assert not missing, f"registry extractors not re-exported from pilothify.extract: {missing}"
    assert not diverged, f"facade object diverges from registry: {diverged}"


def test_terraform_migrated():
    # The concrete anchor from that fix: extract_terraform lives in its own module,
    # and both the facade and the registry point at that one object.
    from pilothify.extractors.terraform import extract_terraform

    assert facade.extract_terraform is extract_terraform
    assert LANGUAGE_EXTRACTORS["terraform"] is extract_terraform
