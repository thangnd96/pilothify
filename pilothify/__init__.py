"""pilothify - extract · build · cluster · analyze · report."""


def __getattr__(name):
    # Lazy imports so `pilothify install` works before heavy deps are in place.
    _map = {
        "extract": ("pilothify.extract", "extract"),
        "collect_files": ("pilothify.extract", "collect_files"),
        "build_from_json": ("pilothify.build", "build_from_json"),
        "cluster": ("pilothify.cluster", "cluster"),
        "score_all": ("pilothify.cluster", "score_all"),
        "cohesion_score": ("pilothify.cluster", "cohesion_score"),
        "god_nodes": ("pilothify.analyze", "god_nodes"),
        "surprising_connections": ("pilothify.analyze", "surprising_connections"),
        "suggest_questions": ("pilothify.analyze", "suggest_questions"),
        "generate": ("pilothify.report", "generate"),
        "to_json": ("pilothify.export", "to_json"),
        "to_html": ("pilothify.export", "to_html"),
        "to_svg": ("pilothify.export", "to_svg"),
        "to_canvas": ("pilothify.export", "to_canvas"),
        "to_wiki": ("pilothify.wiki", "to_wiki"),
        "reflect": ("pilothify.reflect", "reflect"),
        "save_query_result": ("pilothify.ingest", "save_query_result"),
    }
    if name in _map:
        import importlib
        mod_name, attr = _map[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module 'pilothify' has no attribute {name!r}")
