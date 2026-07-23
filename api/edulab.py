#!/usr/bin/env python3
"""
edulab API — 动态出题接口（Vercel Serverless Function）

GET /api/edulab?skill=solid-geometry&type=random&seed=0

Skills: solid-geometry | analytic-geometry | chem-reaction
Types:  random | list | pyramid | cube | box |
        ellipse_dot_range | ellipse_chord_range | ellipse_area_max |
        ellipse_slopeprod_const | parabola_dot_const | hyperbola_ecc_range |
        combustion_ch4 | combustion_h2 | electrolysis_water |
        redox_na_cl2 | esterification | glucose_combustion
"""

import json
import random
import importlib.util
from pathlib import Path
from urllib.parse import parse_qs

EDULAB = Path(__file__).resolve().parent.parent / "edulab"

SKILLS = {
    "solid-geometry": {
        "dir": EDULAB / "skills" / "edu-solid-geometry",
        "types": ["pyramid", "cube", "box"],
        "template": "template/lesson.html",
        "placeholder": "__LESSON_DATA__",
    },
    "analytic-geometry": {
        "dir": EDULAB / "skills" / "edu-analytic-geometry",
        "types": [
            "ellipse_dot_range", "ellipse_chord_range", "ellipse_area_max",
            "ellipse_slopeprod_const", "parabola_dot_const", "hyperbola_ecc_range",
        ],
        "template": "template/board.html",
        "placeholder": "__LESSON_DATA__",
    },
    "chem-reaction": {
        "dir": EDULAB / "skills" / "edu-chem-reaction",
        "types": [
            "combustion_ch4", "combustion_h2", "electrolysis_water",
            "redox_na_cl2", "esterification", "glucose_combustion",
        ],
        "template": "template/reaction.html",
        "placeholder": "__REACTION_DATA__",
    },
}

# Lazy-loaded generate modules (loaded once per cold start, then cached)
_gens = {}


def _load(skill):
    """Load the generate.py module for a skill via importlib."""
    if skill in _gens:
        return _gens[skill]
    cfg = SKILLS[skill]
    gen_path = cfg["dir"] / "scripts" / "generate.py"
    name = f"edulab_{skill.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, str(gen_path))
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = name
    try:
        spec.loader.exec_module(mod)
    except Exception:
        # Retry once — cold-start import ordering can fail
        spec.loader.exec_module(mod)
    _gens[skill] = mod
    return mod


def _generate_data(skill, ptype, seed):
    """Core generation logic — returns (data_dict, cfg)."""
    cfg = SKILLS[skill]
    gen = _load(skill)
    rng = random.Random(seed)

    # ── Solid Geometry ──
    if skill == "solid-geometry":
        if ptype == "random":
            ptype = rng.choice(cfg["types"])

        if ptype == "pyramid":
            base = 1 + rng.randint(1, 4)
            h = round(1 + rng.random() * 4, 1)
            data = gen.build_data(base_edge=base, height=h)
        elif ptype == "cube":
            data = gen.build_cube_data()
        elif ptype == "box":
            lx = rng.randint(2, 6)
            ly = rng.randint(2, 5)
            lz = rng.randint(1, 4)
            data = gen.build_box_volume_data(lx=lx, ly=ly, lz=lz)
        else:
            raise ValueError(f"Unknown solid-geometry type: {ptype}")

        return data, cfg

    # ── Analytic Geometry ──
    elif skill == "analytic-geometry":
        if ptype == "random":
            ptype = rng.choice(cfg["types"])

        if ptype not in gen.REGISTRY:
            raise ValueError(f"Unknown analytic-geometry type: {ptype}")

        data = gen.REGISTRY[ptype]()  # no args; deterministic per type
        return data, cfg

    # ── Chem Reaction ──
    elif skill == "chem-reaction":
        if ptype == "random":
            ptype = rng.choice(cfg["types"])

        if ptype not in gen.REGISTRY:
            raise ValueError(f"Unknown chem-reaction type: {ptype}")

        spec = gen.REGISTRY[ptype]()       # spec dict (no args)
        data = gen.K.assemble_data(spec)   # K = reaction_kernel (as imported in generate.py)
        return data, cfg

    raise ValueError(f"Unknown skill: {skill}")


def _render_html(data, cfg):
    """Read template and inject JSON problem data."""
    data.pop("_answer", None)  # solid-geometry internal assertion key
    template_path = cfg["dir"] / cfg["template"]
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    return html.replace(cfg["placeholder"], json.dumps(data, ensure_ascii=False))


ERROR_HTML = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>edulab Error</title>'
    '<style>body{font-family:system-ui;padding:40px;color:#f1f5f9;background:#0f172a}'
    'h1{color:#ef4444}pre{background:#1e293b;padding:16px;border-radius:8px;overflow-x:auto}'
    '</style></head><body><h1>%s</h1><pre>%s</pre></body></html>'
)


# ── Vercel WSGI handler ──
def handler(environ, start_response):
    qs = environ.get("QUERY_STRING", "")
    params = parse_qs(qs)

    skill = params.get("skill", ["solid-geometry"])[0]
    ptype = params.get("type", ["random"])[0]
    try:
        seed = int(params.get("seed", ["0"])[0])
    except ValueError:
        seed = 0

    # ── type=list → return available types as JSON ──
    if ptype == "list":
        cfg = SKILLS.get(skill)
        if not cfg:
            body = json.dumps({"error": f"Unknown skill: {skill}", "skills": list(SKILLS.keys())})
            start_response("400 Bad Request", [
                ("Content-Type", "application/json"),
                ("Access-Control-Allow-Origin", "*"),
            ])
            return [body.encode("utf-8")]
        avail = list(cfg["types"]) + ["random", "list"]
        body = json.dumps({"skill": skill, "types": avail})
        start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),
        ])
        return [body.encode("utf-8")]

    # ── Validate skill ──
    if skill not in SKILLS:
        html = ERROR_HTML % (
            "Unknown skill",
            f"Skill '{skill}' not found.\nAvailable: {list(SKILLS.keys())}",
        )
        start_response("400 Bad Request", [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
        ])
        return [html.encode("utf-8")]

    # ── Validate type ──
    cfg = SKILLS[skill]
    if ptype != "random" and ptype not in cfg["types"]:
        html = ERROR_HTML % (
            "Unknown type",
            f"Type '{ptype}' not available for skill '{skill}'.\n"
            f"Available: {cfg['types'] + ['random', 'list']}",
        )
        start_response("400 Bad Request", [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
        ])
        return [html.encode("utf-8")]

    # ── Generate ──
    try:
        data, cfg = _generate_data(skill, ptype, seed)
        html = _render_html(data, cfg)
        start_response("200 OK", [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
        ])
        return [html.encode("utf-8")]
    except Exception:
        import traceback
        html = ERROR_HTML % ("Generation Error", traceback.format_exc())
        start_response("500 Internal Server Error", [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
        ])
        return [html.encode("utf-8")]

# Vercel Python runtime: some versions look for 'app' as the WSGI callable
app = handler
