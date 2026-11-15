"""Routes served by web handlers outside Java Spring.

Spring handlers get their route in the Java walk. This pass covers the other
common frameworks and runs after a file's extraction:

- FastAPI and Flask: ``@app.get("/x")``, ``@router.post(...)``,
  ``@bp.route("/x", methods=[...])``, joined to the ``prefix=`` or
  ``url_prefix=`` of an ``APIRouter`` or ``Blueprint`` assigned in the same file.
  The route goes on the function.
- NestJS: ``@Controller('users')`` on the class and ``@Get(':id')`` on the
  method. The route goes on the method.
- Express, Koa router, Fastify, Hono: ``router.get('/x', handler)`` and
  ``router.route('/x').get(handler)``, only in a file that imports one of them,
  so a client call such as ``axios.get('/x', data)`` is never read as a route.
  Handlers are often inline, so each registration becomes a route node the file
  contains, with a ``calls`` edge to the handler when it is a function declared
  in the same file.

A mount prefix set elsewhere (``include_router``, ``app.use('/api', r)``,
``setGlobalPrefix``) is not known here, so those routes carry only their own
part; ``route_links`` matches a doc naming the full path by suffix.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pilothify.extractors.base import _file_stem, _make_id, _read_source_bytes

_PY_VERBS = ("get", "post", "put", "patch", "delete", "options", "head")
_JS_VERBS = (*_PY_VERBS, "all")
_NEST_VERBS = {"Get", "Post", "Put", "Patch", "Delete", "Options", "Head", "All"}
_JS_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}
_TS_SUFFIXES = {".ts", ".tsx", ".mts", ".cts"}

# Cheap byte checks so a file with no route syntax is never parsed twice.
_PY_HINT = re.compile(rb"@[\w.]+\.(?:get|post|put|patch|delete|options|head|route|api_route)\s*\(")
_NEST_HINT = re.compile(rb"@Controller\s*\(")
# A value import or require of a server library; `import type { Request }
# from 'express'` (common in NestJS services) brings no server and must not count.
_JS_SERVER_IMPORT = re.compile(
    rb"""require\s*\(\s*['"](?:express|@koa/router|koa-router|fastify|hono)['"]"""
    rb"""|^[ \t]*import\s+(?!type\b)[^;]*?\bfrom\s+['"](?:express|@koa/router|koa-router|fastify|hono)['"]""",
    re.M,
)
# Receivers that register routes: names bound in the file from one of these
# factories, plus the names servers conventionally get. Anything else, such as
# `axios`, `this.http` or an `api` client, is a client call, not a route.
_SERVER_FACTORIES = {"express", "Router", "fastify", "Fastify", "Hono", "KoaRouter", "Koa"}
_SERVER_NAMES = {"app", "router", "server", "fastify"}
_FLASK_PARAM = re.compile(r"<(?:[^<>:]+:)?([^<>:]+)>")


@lru_cache(maxsize=None)
def _parser(lang: str):
    from tree_sitter import Language, Parser

    if lang == "python":
        import tree_sitter_python as grammar

        return Parser(Language(grammar.language()))
    if lang == "javascript":
        import tree_sitter_javascript as grammar

        return Parser(Language(grammar.language()))
    import tree_sitter_typescript as grammar

    return Parser(Language(grammar.language_tsx() if lang == "tsx" else grammar.language_typescript()))


def _text(node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", "replace") if node is not None else ""


def _walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _string_value(node, source: bytes) -> str | None:
    """A plain string literal's value; None for anything interpolated or computed."""
    if node is None or node.type not in ("string", "template_string"):
        return None
    if any(c.type in ("interpolation", "template_substitution") for c in node.children):
        return None
    return "".join(_text(c, source) for c in node.children
                   if c.type in ("string_content", "string_fragment"))


def _join(*parts: str) -> str:
    return "/" + "/".join(seg for part in parts for seg in part.strip().split("/") if seg)


def _by_label_and_line(result: dict) -> dict[tuple[str, int], dict]:
    out: dict[tuple[str, int], dict] = {}
    for node in result.get("nodes", []):
        loc = str(node.get("source_location") or "")
        if loc.startswith("L") and loc[1:].isdigit():
            out.setdefault((str(node.get("label")), int(loc[1:])), node)
    return out


def _set_route(node: dict | None, route: str) -> None:
    if node is not None:
        node.setdefault("attributes", {})["route"] = route


# --- FastAPI / Flask -----------------------------------------------------------

def _python_prefixes(root, source: bytes) -> dict[str, str]:
    """Module-level ``x = APIRouter(prefix=...)`` / ``Blueprint(url_prefix=...)``."""
    prefixes: dict[str, str] = {}
    for stmt in root.children:
        assign = stmt.named_children[0] if stmt.type == "expression_statement" and stmt.named_children else None
        if assign is None or assign.type != "assignment":
            continue
        target, value = assign.child_by_field_name("left"), assign.child_by_field_name("right")
        if target is None or target.type != "identifier" or value is None or value.type != "call":
            continue
        if _text(value.child_by_field_name("function"), source).rsplit(".", 1)[-1] not in ("APIRouter", "Blueprint"):
            continue
        args = value.child_by_field_name("arguments")
        for arg in args.named_children if args else ():
            if arg.type == "keyword_argument" and _text(arg.child_by_field_name("name"), source) in ("prefix", "url_prefix"):
                prefix = _string_value(arg.child_by_field_name("value"), source)
                if prefix is not None:
                    prefixes[_text(target, source)] = prefix
    return prefixes


def _python_decorator_route(decorator, source: bytes, prefixes: dict[str, str]) -> str | None:
    call = decorator.named_children[0] if decorator.named_children else None
    if call is None or call.type != "call":
        return None
    fn = call.child_by_field_name("function")
    if fn is None or fn.type != "attribute":
        return None
    attr = _text(fn.child_by_field_name("attribute"), source)
    args = call.child_by_field_name("arguments")
    named = args.named_children if args else []
    positional = [a for a in named if a.type != "keyword_argument"]
    keywords = {_text(a.child_by_field_name("name"), source): a.child_by_field_name("value")
                for a in named if a.type == "keyword_argument"}
    if attr in _PY_VERBS:
        verbs = [attr.upper()]
    elif attr in ("route", "api_route"):
        methods = keywords.get("methods")
        listed = [_string_value(m, source) for m in (methods.named_children if methods is not None else [])]
        verbs = list(dict.fromkeys(v.upper() for v in listed if v)) or ["GET"]
    else:
        return None
    path = _string_value(positional[0], source) if positional else _string_value(keywords.get("path"), source)
    receiver = fn.child_by_field_name("object")
    prefix = prefixes.get(_text(receiver, source), "") if receiver is not None and receiver.type == "identifier" else ""
    if path is None or not (path.startswith("/") or (path == "" and prefix)):
        return None
    # Flask writes parameters as <name> or <converter:name>; store them the way
    # FastAPI, Spring and docs do, so route_links can fold them.
    joined = _FLASK_PARAM.sub(r"{\1}", _join(prefix, path))
    return ", ".join(f"{verb} {joined}" for verb in verbs)


def _python_routes(tree, source: bytes, result: dict) -> None:
    prefixes = _python_prefixes(tree.root_node, source)
    nodes = _by_label_and_line(result)
    for decorated in _walk(tree.root_node):
        if decorated.type != "decorated_definition":
            continue
        definition = decorated.child_by_field_name("definition")
        if definition is None or definition.type != "function_definition":
            continue
        for decorator in decorated.children:
            if decorator.type != "decorator":
                continue
            route = _python_decorator_route(decorator, source, prefixes)
            if route:
                name = _text(definition.child_by_field_name("name"), source)
                line = definition.start_point[0] + 1
                _set_route(nodes.get((f"{name}()", line)) or nodes.get((f".{name}()", line)), route)
                break


# --- NestJS --------------------------------------------------------------------

def _decorator_call(decorator, source: bytes) -> tuple[str, list]:
    expr = decorator.named_children[0] if decorator.named_children else None
    if expr is None:
        return "", []
    if expr.type == "call_expression":
        args = expr.child_by_field_name("arguments")
        name = _text(expr.child_by_field_name("function"), source).rsplit(".", 1)[-1]
        return name, [a for a in (args.named_children if args else []) if a.type != "comment"]
    return _text(expr, source).rsplit(".", 1)[-1], []


def _nest_controller_prefix(cls, source: bytes) -> str | None:
    """The class's @Controller path; None when it has none or it is not a literal."""
    decorators = [c for c in cls.children if c.type == "decorator"]
    if cls.parent is not None and cls.parent.type == "export_statement":
        decorators += [c for c in cls.parent.children if c.type == "decorator"]
    for decorator in decorators:
        name, args = _decorator_call(decorator, source)
        if name != "Controller":
            continue
        if not args:
            return ""
        literal = _string_value(args[0], source)
        if literal is not None:
            return literal
        if args[0].type == "object":
            for pair in args[0].named_children:
                if pair.type == "pair" and _text(pair.child_by_field_name("key"), source).strip("'\"") == "path":
                    return _string_value(pair.child_by_field_name("value"), source)
            return ""
        return None
    return None


def _nest_method_route(decorator, source: bytes, prefix: str) -> str | None:
    name, args = _decorator_call(decorator, source)
    if name not in _NEST_VERBS:
        return None
    path = _string_value(args[0], source) if args else ""
    if path is None:
        return None
    return f"{name.upper()} {_join(prefix, path)}"


def _nest_routes(tree, source: bytes, result: dict) -> None:
    nodes = _by_label_and_line(result)
    for cls in _walk(tree.root_node):
        if cls.type not in ("class_declaration", "abstract_class_declaration", "class"):
            continue
        prefix = _nest_controller_prefix(cls, source)
        body = cls.child_by_field_name("body")
        if prefix is None or body is None:
            continue
        pending: list = []
        for child in body.children:
            if child.type == "decorator":
                pending.append(child)
                continue
            if child.type == "comment":  # a comment between decorator and method
                continue
            if child.type == "method_definition":
                decorators = pending + [c for c in child.children if c.type == "decorator"]
                route = next((r for d in decorators if (r := _nest_method_route(d, source, prefix))), None)
                name = child.child_by_field_name("name")
                if route and name is not None:
                    _set_route(nodes.get((f".{_text(name, source)}()", name.start_point[0] + 1)), route)
            pending = []


# --- Express, Koa router, Fastify, Hono ----------------------------------------

def _chained_route_path(call, source: bytes) -> str | None:
    """The path of ``x.route('/p')`` at the base of ``x.route('/p').get(..).post(..)``."""
    while call is not None and call.type == "call_expression":
        fn = call.child_by_field_name("function")
        if fn is None or fn.type != "member_expression":
            return None
        prop = _text(fn.child_by_field_name("property"), source)
        if prop == "route":
            args = call.child_by_field_name("arguments")
            first = args.named_children[0] if args is not None and args.named_children else None
            return _string_value(first, source)
        if prop not in _JS_VERBS:
            return None
        call = fn.child_by_field_name("object")
    return None


def _server_bindings(root, source: bytes) -> set[str]:
    """Names bound in the file to a server or router: ``const app = express()``,
    ``const r = express.Router()``, ``const router = new Router()``."""
    names: set[str] = set()
    for node in _walk(root):
        if node.type != "variable_declarator":
            continue
        name, value = node.child_by_field_name("name"), node.child_by_field_name("value")
        if name is None or name.type != "identifier" or value is None:
            continue
        callee = value.child_by_field_name("function" if value.type == "call_expression" else "constructor") \
            if value.type in ("call_expression", "new_expression") else None
        text = _text(callee, source)
        if callee is not None and (text.rsplit(".", 1)[-1] in _SERVER_FACTORIES or text.startswith("require(")):
            names.add(_text(name, source))
    return names


def _chain_base(node, source: bytes) -> str:
    """The identifier at the base of ``router.route('/p').get(h).post(h)``."""
    while node is not None and node.type in ("call_expression", "member_expression"):
        node = node.child_by_field_name("function" if node.type == "call_expression" else "object")
    return _text(node, source) if node is not None and node.type == "identifier" else ""


def _js_server_routes(tree, source: bytes, result: dict, path: Path) -> None:
    file_node = next((n for n in result.get("nodes", []) if n.get("label") == path.name), None)
    if file_node is None:
        return
    functions = {str(n["label"])[:-2]: n["id"] for n in result.get("nodes", [])
                 if str(n.get("label", "")).endswith("()") and not str(n["label"]).startswith(".")}
    servers = _server_bindings(tree.root_node, source) | _SERVER_NAMES
    seen = {n["id"] for n in result.get("nodes", [])}
    stem = _file_stem(path)
    for call in _walk(tree.root_node):
        if call.type != "call_expression":
            continue
        fn = call.child_by_field_name("function")
        if fn is None or fn.type != "member_expression":
            continue
        verb = _text(fn.child_by_field_name("property"), source)
        if verb not in _JS_VERBS:
            continue
        receiver = fn.child_by_field_name("object")
        if _chain_base(receiver, source) not in servers:
            continue
        args = call.child_by_field_name("arguments")
        argv = [a for a in (args.named_children if args else []) if a.type != "comment"]
        first = _string_value(argv[0], source) if argv else None
        if first is not None:
            # `router.get('/', h)`, also further down a chain:
            # `router.get('/', h).post('/users', h)`
            if len(argv) < 2:
                continue
            route_path, handlers = first, argv[1:]
        elif receiver is not None and receiver.type == "call_expression":
            route_path, handlers = _chained_route_path(receiver, source), argv
        else:
            continue
        if route_path is None or not route_path.startswith("/") or not handlers:
            continue
        handler = handlers[-1]
        if handler.type not in ("identifier", "member_expression", "arrow_function",
                                "function_expression", "function", "call_expression"):
            continue
        if handler.type == "call_expression":  # asyncHandler(listUsers)
            wrapped = handler.child_by_field_name("arguments")
            handler = next((a for a in (wrapped.named_children if wrapped else [])
                            if a.type == "identifier"), handler)
        route = f"{verb.upper()} {_join(route_path)}"
        line = f"L{call.start_point[0] + 1}"
        rid = _make_id(stem, "route", verb.upper(), route_path)
        if rid in seen:
            continue
        seen.add(rid)
        result["nodes"].append({
            "id": rid, "label": route, "file_type": "code",
            "source_file": file_node.get("source_file"), "source_location": line,
            "attributes": {"route": route},
        })
        result["edges"].append({
            "source": file_node["id"], "target": rid, "relation": "contains",
            "confidence": "EXTRACTED", "source_file": file_node.get("source_file"),
            "source_location": line, "weight": 1.0,
        })
        target = functions.get(_text(handler, source)) if handler.type == "identifier" else None
        if target is not None:
            result["edges"].append({
                "source": rid, "target": target, "relation": "calls", "context": "route",
                "confidence": "EXTRACTED", "source_file": file_node.get("source_file"),
                "source_location": line, "weight": 1.0,
            })


def attach_web_routes(path: Path, result: dict) -> None:
    """Stamp routes on this file's handlers (and add Express-style route nodes).

    Never raises: a file this pass cannot read keeps its extraction unchanged."""
    if "error" in result:
        return
    suffix = path.suffix.lower()
    if suffix != ".py" and suffix not in _JS_SUFFIXES:
        return
    try:
        source = _read_source_bytes(path)
        if suffix == ".py":
            if _PY_HINT.search(source):
                _python_routes(_parser("python").parse(source), source, result)
            return
        nest = suffix in _TS_SUFFIXES and _NEST_HINT.search(source)
        server = _JS_SERVER_IMPORT.search(source)
        if not (nest or server):
            return
        lang = "tsx" if suffix == ".tsx" else "typescript" if suffix in _TS_SUFFIXES else "javascript"
        tree = _parser(lang).parse(source)
        if nest:
            _nest_routes(tree, source, result)
        if server:
            _js_server_routes(tree, source, result, path)
    except Exception:
        return
