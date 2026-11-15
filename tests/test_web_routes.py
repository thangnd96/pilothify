"""NestJS, FastAPI/Flask and Express-style handlers carry the route they serve."""
from __future__ import annotations

import networkx as nx

from pilothify.extract import extract
from pilothify.route_links import ROUTE_RELATION, link_routes

NEST = """\
import { Controller, Get, Post, Delete } from '@nestjs/common';

@Controller('users')
export class UsersController {
  @Get(':id')
  findOne() { return 1; }

  @Post()
  create() { return 1; }

  @Delete(PATHS.ME)
  computed() { return 1; }

  helper() { return 1; }
}

@Controller({ path: 'teams' })
export class TeamsController {
  @Get('members/:teamId')
  members() { return 1; }
}

@Controller(['a', 'b'])
export class ManyController {
  @Get('x')
  many() { return 1; }
}
"""

FASTAPI = """\
from fastapi import APIRouter, FastAPI
from flask import Blueprint

app = FastAPI()
router = APIRouter(prefix="/items")
bp = Blueprint("admin", __name__, url_prefix="/admin")

@router.get("/{item_id}")
def read_item(item_id: int):
    return item_id

@app.post("/login")
async def login():
    return 1

@bp.route("/users", methods=["DELETE"])
def drop_users():
    return 1

@app.get(f"/dyn/{1}")
def dynamic():
    return 1

@cache.memoize(60)
def not_a_route():
    return 1
"""

EXPRESS = """\
const express = require('express');
const router = express.Router();
function listUsers(req, res) { res.send([]); }
router.get('/users', listUsers);
router.post('/users/:id/ban', auth, (req, res) => res.send(1));
router.route('/teams').get(listUsers).delete((req, res) => res.end());
app.get('title');
router.get(`/v/${version}`, listUsers);
module.exports = router;
"""

CLIENT = """\
import axios from 'axios';
export function save(payload) { return axios.post('/users', payload); }
export const load = () => api.get('/users/1', handler);
"""


def _extract(tmp_path, files: dict[str, str]) -> dict:
    paths = []
    for name, text in files.items():
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return extract(paths, cache_root=tmp_path)


def _routes(result: dict) -> dict[str, str]:
    return {n["label"]: n["attributes"]["route"] for n in result["nodes"]
            if isinstance(n.get("attributes"), dict) and n["attributes"].get("route")}


def test_nestjs_methods_join_the_controller_path(tmp_path):
    routes = _routes(_extract(tmp_path, {"users.controller.ts": NEST}))
    assert routes == {
        ".findOne()": "GET /users/:id",
        ".create()": "POST /users",
        ".members()": "GET /teams/members/:teamId",
    }


def test_fastapi_and_flask_handlers_join_their_router_prefix(tmp_path):
    routes = _routes(_extract(tmp_path, {"api.py": FASTAPI}))
    assert routes == {
        "read_item()": "GET /items/{item_id}",
        "login()": "POST /login",
        "drop_users()": "DELETE /admin/users",
    }


def test_express_registrations_become_route_nodes_linked_to_named_handlers(tmp_path):
    result = _extract(tmp_path, {"server.js": EXPRESS})
    routes = _routes(result)
    assert routes == {
        "GET /users": "GET /users",
        "POST /users/:id/ban": "POST /users/:id/ban",
        "GET /teams": "GET /teams",
        "DELETE /teams": "DELETE /teams",
    }
    by_id = {n["id"]: n["label"] for n in result["nodes"]}
    calls = {(by_id[e["source"]], by_id[e["target"]]) for e in result["edges"]
             if e.get("context") == "route"}
    assert calls == {("GET /users", "listUsers()"), ("GET /teams", "listUsers()")}
    contains = {by_id[e["target"]] for e in result["edges"]
                if e["relation"] == "contains" and by_id.get(e["source"]) == "server.js"}
    assert set(routes) <= contains
    assert not any(str(e["source"]).startswith("/") for e in result["edges"])  # ids are portable


def test_client_calls_in_a_file_without_a_server_import_are_not_routes(tmp_path):
    assert _routes(_extract(tmp_path, {"client.ts": CLIENT})) == {}


def _graph_with(route: str) -> nx.Graph:
    G = nx.Graph()
    G.add_node("h", label="read_item()", file_type="code", source_file="api.py",
               attributes={"route": route})
    return G


def test_a_doc_naming_the_full_mounted_path_links_to_a_shorter_route():
    G = _graph_with("GET /items/{item_id}")
    G.add_node("doc", label="Đọc item qua GET /api/v1/items/{id}", file_type="document",
               source_file="docs/api.md")
    assert link_routes(G) == 1
    edge = G.edges["doc", "h"]
    assert edge["relation"] == ROUTE_RELATION and edge["confidence"] == "INFERRED"


def test_a_one_segment_tail_does_not_link():
    G = _graph_with("GET /items")
    G.add_node("doc", label="GET /api/v1/items", file_type="document", source_file="docs/api.md")
    assert link_routes(G) == 0
