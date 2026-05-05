import json
import re
from pathlib import Path

try:
    import yaml as _yaml  # type: ignore[import-untyped]
    _YAML_AVAILABLE = True
except ImportError:
    _yaml = None  # type: ignore[assignment]
    _YAML_AVAILABLE = False


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def _file_type(path: str) -> str:
    p = Path(path)
    name = p.name.lower()
    ext = p.suffix.lower()
    if name == "dockerfile" or name.startswith("dockerfile.") or ext == ".dockerfile":
        return "dockerfile"
    if ext in {".yml", ".yaml"}:
        return "yaml"
    if ext == ".json":
        return "json"
    return "unknown"


# ── JSON ──────────────────────────────────────────────────────────────────────

def _json_load(path: str) -> tuple[object | None, str | None]:
    src = _read(path)
    if src is None:
        return None, f"File not found: {path}"
    try:
        return json.loads(src), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error in {path}: {e}"


def _json_value_preview(v: object) -> str:
    if isinstance(v, dict):
        return f"{{...}} ({len(v)} keys)"
    if isinstance(v, list):
        return f"[...] ({len(v)} items)"
    s = repr(v)
    return s[:80] + "…" if len(s) > 80 else s


def _json_structure(data: object) -> str:
    if isinstance(data, dict):
        return "\n".join(data.keys()) if data else "(empty object)"
    if isinstance(data, list):
        return f"(array of {len(data)} items)"
    return type(data).__name__


def _json_skeleton(data: object) -> str:
    if isinstance(data, dict):
        return "\n".join(f"{k}: {_json_value_preview(v)}" for k, v in data.items())
    if isinstance(data, list):
        return f"(array of {len(data)} items)"
    return repr(data)[:200]


def _json_symbol_body(data: object, name: str) -> str:
    if not isinstance(data, dict):
        return f"Cannot look up key '{name}': root is not an object"
    if name not in data:
        return f"Key '{name}' not found. Top-level keys: {', '.join(data.keys())}"
    return json.dumps(data[name], indent=2)


def _json_imports(path: str) -> str:
    src = _read(path)
    if src is None:
        return f"File not found: {path}"
    refs = re.findall(r'"\\$ref"\s*:\s*"([^"]+)"', src)
    return "\n".join(refs) if refs else "(no $ref imports)"


# ── YAML ──────────────────────────────────────────────────────────────────────

def _yaml_load(path: str) -> tuple[object | None, str | None]:
    if not _YAML_AVAILABLE or _yaml is None:
        return None, "PyYAML not installed. Run: pip install pyyaml"
    src = _read(path)
    if src is None:
        return None, f"File not found: {path}"
    try:
        return _yaml.safe_load(src), None
    except _yaml.YAMLError as e:
        return None, f"YAML parse error in {path}: {e}"


def _yaml_symbol_body(data: object, name: str) -> str:
    if _yaml is None:
        return "PyYAML not installed. Run: pip install pyyaml"
    if not isinstance(data, dict):
        return f"Cannot look up key '{name}': root is not a mapping"
    if name not in data:
        return f"Key '{name}' not found. Top-level keys: {', '.join(str(k) for k in data.keys())}"
    return _yaml.dump(data[name], default_flow_style=False).rstrip()


def _yaml_imports(path: str) -> str:
    src = _read(path)
    if src is None:
        return f"File not found: {path}"
    anchors = re.findall(r"&(\w+)", src)
    includes = re.findall(r"!include\s+(\S+)", src)
    parts: list[str] = []
    if anchors:
        parts.append("anchors: " + ", ".join(anchors))
    if includes:
        parts.append("includes: " + ", ".join(includes))
    return "\n".join(parts) if parts else "(no anchors or includes)"


# ── Dockerfile ────────────────────────────────────────────────────────────────

def _parse_dockerfile(content: str) -> list[tuple[str, str]]:
    instructions: list[tuple[str, str]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        instructions.append((parts[0].upper(), parts[1] if len(parts) > 1 else ""))
    return instructions


def _dockerfile_stages(instructions: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Returns (stage_name, base_image) pairs. Anonymous stages get names like stage0."""
    stages = []
    idx = 0
    for inst, args in instructions:
        if inst == "FROM":
            parts = args.split()
            base = parts[0]
            name = parts[parts.index("AS") + 1] if "AS" in [p.upper() for p in parts] else f"stage{idx}"
            stages.append((name, base))
            idx += 1
    return stages


def _dockerfile_structure(instructions: list[tuple[str, str]]) -> str:
    stages = _dockerfile_stages(instructions)
    types_used = sorted({inst for inst, _ in instructions})
    lines = []
    if stages:
        lines.append("stages: " + ", ".join(n for n, _ in stages))
    lines.append("instructions: " + " ".join(types_used))
    return "\n".join(lines)


def _dockerfile_skeleton(instructions: list[tuple[str, str]]) -> str:
    key_types = {"FROM", "CMD", "ENTRYPOINT", "EXPOSE", "ENV", "ARG", "WORKDIR", "USER"}
    lines = []
    for inst, args in instructions:
        if inst in key_types:
            lines.append(f"{inst} {args}")
    return "\n".join(lines) if lines else "(empty)"


def _dockerfile_symbol_body(instructions: list[tuple[str, str]], name: str) -> str:
    stages = _dockerfile_stages(instructions)
    stage_names = [n for n, _ in stages]

    if name.upper() in {inst for inst, _ in instructions}:
        matched = [f"{inst} {args}" for inst, args in instructions if inst == name.upper()]
        return "\n".join(matched)

    if name not in stage_names:
        return f"Stage '{name}' not found. Stages: {', '.join(stage_names) or 'none'}"

    stage_idx = stage_names.index(name)
    start = 0
    from_count = 0
    for i, (inst, _) in enumerate(instructions):
        if inst == "FROM":
            if from_count == stage_idx:
                start = i
                break
            from_count += 1

    end = len(instructions)
    for i, (inst, _) in enumerate(instructions[start + 1:], start + 1):
        if inst == "FROM":
            end = i
            break

    return "\n".join(f"{inst} {args}" for inst, args in instructions[start:end])


def _dockerfile_imports(instructions: list[tuple[str, str]]) -> str:
    froms = [f"FROM {args}" for inst, args in instructions if inst == "FROM"]
    return "\n".join(froms) if froms else "(no FROM instructions)"


# ── Public interface ──────────────────────────────────────────────────────────

def structure(path: str) -> str:
    """Flat orientation view of a config file."""
    ft = _file_type(path)
    if ft == "json":
        data, err = _json_load(path)
        return err or _json_structure(data)
    if ft == "yaml":
        data, err = _yaml_load(path)
        return err or _json_structure(data)
    if ft == "dockerfile":
        src = _read(path)
        if src is None:
            return f"File not found: {path}"
        return _dockerfile_structure(_parse_dockerfile(src))
    return f"Unknown config type: {path}"


def skeleton(path: str) -> str:
    """Top-level shape: keys + value previews (JSON/YAML) or key instructions (Dockerfile)."""
    ft = _file_type(path)
    if ft == "json":
        data, err = _json_load(path)
        return err or _json_skeleton(data)
    if ft == "yaml":
        data, err = _yaml_load(path)
        return err or _json_skeleton(data)
    if ft == "dockerfile":
        src = _read(path)
        if src is None:
            return f"File not found: {path}"
        return _dockerfile_skeleton(_parse_dockerfile(src))
    return f"Unknown config type: {path}"


def symbol_body(path: str, name: str) -> str:
    """Full value of a named key (JSON/YAML) or stage/instruction group (Dockerfile)."""
    ft = _file_type(path)
    if ft == "json":
        data, err = _json_load(path)
        return err or _json_symbol_body(data, name)
    if ft == "yaml":
        data, err = _yaml_load(path)
        return err or _yaml_symbol_body(data, name)
    if ft == "dockerfile":
        src = _read(path)
        if src is None:
            return f"File not found: {path}"
        return _dockerfile_symbol_body(_parse_dockerfile(src), name)
    return f"Unknown config type: {path}"


def imports(path: str) -> str:
    """$ref strings (JSON), anchors/includes (YAML), or FROM lines (Dockerfile)."""
    ft = _file_type(path)
    if ft == "json":
        return _json_imports(path)
    if ft == "yaml":
        return _yaml_imports(path)
    if ft == "dockerfile":
        src = _read(path)
        if src is None:
            return f"File not found: {path}"
        return _dockerfile_imports(_parse_dockerfile(src))
    return f"Unknown config type: {path}"
