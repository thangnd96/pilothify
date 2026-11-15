"""Per-language extractors, incrementally migrated out of pilothify/extract.py.

Dispatch still flows through pilothify.extract (the facade re-exports every
moved name), so importing from pilothify.extract keeps working unchanged.
LANGUAGE_EXTRACTORS is the registry seed; wiring dispatch through it is a
later, separate step. See MIGRATION.md for how to port another language.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from pilothify.extractors.apex import extract_apex
from pilothify.extractors.bash import extract_bash
from pilothify.extractors.blade import extract_blade
from pilothify.extractors.cobol import extract_cobol
from pilothify.extractors.commonlisp import extract_commonlisp
from pilothify.extractors.dart import extract_dart
from pilothify.extractors.dm import extract_dm, extract_dmf, extract_dmi, extract_dmm
from pilothify.extractors.elixir import extract_elixir
from pilothify.extractors.erlang import extract_erlang
from pilothify.extractors.fortran import extract_fortran
from pilothify.extractors.go import extract_go
from pilothify.extractors.json_config import extract_json
from pilothify.extractors.julia import extract_julia
from pilothify.extractors.markdown import extract_markdown
from pilothify.extractors.objc import extract_objc
from pilothify.extractors.pascal import extract_pascal
from pilothify.extractors.pascal_forms import extract_delphi_form, extract_lazarus_form
from pilothify.extractors.powershell import extract_powershell, extract_powershell_manifest
from pilothify.extractors.r import extract_r
from pilothify.extractors.razor import extract_razor
from pilothify.extractors.rust import extract_rust
from pilothify.extractors.sln import extract_sln
from pilothify.extractors.solidity import extract_solidity
from pilothify.extractors.sql import extract_sql
from pilothify.extractors.terraform import extract_terraform
from pilothify.extractors.verilog import extract_verilog
from pilothify.extractors.vbnet import extract_vbnet
from pilothify.extractors.zig import extract_zig

LANGUAGE_EXTRACTORS: dict[str, Callable[[Path], dict]] = {
    "apex": extract_apex,
    "bash": extract_bash,
    "blade": extract_blade,
    "cobol": extract_cobol,
    "commonlisp": extract_commonlisp,
    "dart": extract_dart,
    "delphi_form": extract_delphi_form,
    "dm": extract_dm,
    "dmf": extract_dmf,
    "dmi": extract_dmi,
    "dmm": extract_dmm,
    "elixir": extract_elixir,
    "erlang": extract_erlang,
    "fortran": extract_fortran,
    "go": extract_go,
    "json": extract_json,
    "julia": extract_julia,
    "lazarus_form": extract_lazarus_form,
    "markdown": extract_markdown,
    "objc": extract_objc,
    "pascal": extract_pascal,
    "powershell": extract_powershell,
    "powershell_manifest": extract_powershell_manifest,
    "r": extract_r,
    "razor": extract_razor,
    "rust": extract_rust,
    "sln": extract_sln,
    "solidity": extract_solidity,
    "sql": extract_sql,
    "terraform": extract_terraform,
    "verilog": extract_verilog,
    "vbnet": extract_vbnet,
    "zig": extract_zig,
}
