"""The AST cache namespace must include the tree-sitter grammar set:
upgrading a grammar package must invalidate cached extractions produced by
the old grammar, even when the pilothify version and source files are
unchanged."""
from __future__ import annotations

import pytest

import pilothify.cache as cache_mod


@pytest.fixture(autouse=True)
def _reset_grammar_fp_cache(monkeypatch):
    monkeypatch.setattr(cache_mod, "_GRAMMAR_FINGERPRINT_CACHE", None)


def test_ast_cache_dir_is_grammar_namespaced(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "_PILOTHIFY_OUT", str(tmp_path / "out"))
    d = cache_mod.cache_dir(tmp_path, kind="ast")
    name = d.name
    assert name.startswith(f"v{cache_mod._EXTRACTOR_VERSION}-s{cache_mod._AST_CACHE_SCHEMA}-g"), name
    assert name.endswith(cache_mod._grammar_fingerprint()), name


def test_ast_cache_dir_changes_when_grammar_set_changes(tmp_path, monkeypatch):
    """End-to-end of the fix: a grammar upgrade moves the AST cache to a new
    directory, so stale pre-upgrade entries are never served."""
    import importlib.metadata as md

    import pilothify.cache as c

    class _D:
        def __init__(self, name, version):
            self.version = version
            self.metadata = {"Name": name}

    monkeypatch.setattr(c, "_PILOTHIFY_OUT", str(tmp_path / "out"))
    monkeypatch.setattr(md, "distributions", lambda: [_D("tree-sitter-swift", "0.7.2")])
    monkeypatch.setattr(c, "_GRAMMAR_FINGERPRINT_CACHE", None)
    d1 = c.cache_dir(tmp_path, kind="ast")
    monkeypatch.setattr(md, "distributions", lambda: [_D("tree-sitter-swift", "0.7.4")])
    monkeypatch.setattr(c, "_GRAMMAR_FINGERPRINT_CACHE", None)
    monkeypatch.setattr(c, "_cleaned_ast_dirs", set())
    d2 = c.cache_dir(tmp_path, kind="ast")
    assert d1 != d2


def test_grammar_fingerprint_changes_with_grammar_versions(monkeypatch):
    import pilothify.cache as c

    class _D:
        def __init__(self, name, version):
            self.version = version
            self.metadata = {"Name": name}

    import importlib.metadata as md

    monkeypatch.setattr(md, "distributions", lambda: [_D("tree-sitter", "0.25.2"), _D("tree-sitter-swift", "0.7.2")])
    monkeypatch.setattr(c, "_GRAMMAR_FINGERPRINT_CACHE", None)
    fp1 = c._grammar_fingerprint()
    monkeypatch.setattr(md, "distributions", lambda: [_D("tree-sitter", "0.25.2"), _D("tree-sitter-swift", "0.7.4")])
    monkeypatch.setattr(c, "_GRAMMAR_FINGERPRINT_CACHE", None)
    fp2 = c._grammar_fingerprint()
    assert fp1 != fp2


def test_grammar_fingerprint_stable_for_same_set(monkeypatch):
    import pilothify.cache as c

    class _D:
        def __init__(self, name, version):
            self.version = version
            self.metadata = {"Name": name}

    import importlib.metadata as md

    monkeypatch.setattr(md, "distributions", lambda: [_D("tree-sitter", "0.25.2"), _D("tree-sitter-swift", "0.7.4")])
    fp1 = c._grammar_fingerprint()
    monkeypatch.setattr(c, "_GRAMMAR_FINGERPRINT_CACHE", None)  # force recompute
    assert c._grammar_fingerprint() == fp1


def test_a_pool_worker_adopts_the_parents_cache_namespace(tmp_path, monkeypatch):
    """A spawn worker must write where its parent reads, even when it would read
    a different version from package metadata (a rebuilt in-tree egg-info)."""
    import pilothify.cache as c
    from pilothify.extract import _worker_init

    for name in ("_EXTRACTOR_VERSION", "_AST_CACHE_SCHEMA", "_GRAMMAR_FINGERPRINT_CACHE"):
        monkeypatch.setattr(c, name, getattr(c, name))
    parent = ("0.1.3", c._AST_CACHE_SCHEMA, "abc123def456")
    monkeypatch.setattr(c, "_EXTRACTOR_VERSION", "0.1.4")  # what the worker read itself
    _worker_init({}, parent)
    assert c.cache_namespace() == parent
    assert c.cache_dir(tmp_path).name == f"v0.1.3-s{parent[1]}-gabc123def456"
