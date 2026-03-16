"""
Minimal YAML safe_load / dump for the subset used by nightctl.
Handles: flat dicts, nested dicts, lists of scalars, lists of dicts.
Replaces pyyaml until it is available in the environment.
"""


# ─── LOADER ────────────────────────────────────────────────────────────────────

def safe_load(source):
    if hasattr(source, "read"):
        source = source.read()
    lines = source.splitlines()
    result, _ = _parse_value(lines, 0, 0)
    return result


def _indent_of(line):
    return len(line) - len(line.lstrip(" "))


def _is_blank(line):
    s = line.strip()
    return not s or s.startswith("#")


def _parse_scalar(s):
    s = s.strip()
    if not s or s in ("null", "~"):
        return None
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1].replace('\\"', '"')
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x.strip()) for x in _split_csv(inner)]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _split_csv(s):
    parts, depth, current = [], 0, []
    for ch in s:
        if ch in ("[", "("):
            depth += 1; current.append(ch)
        elif ch in ("]", ")"):
            depth -= 1; current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip()); current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return parts


def _next_nonblank(lines, start):
    i = start
    while i < len(lines) and _is_blank(lines[i]):
        i += 1
    return i


def _parse_value(lines, start, base_indent):
    """
    Parse a YAML value (dict, list, or scalar) starting at line `start`.
    All meaningful lines at `base_indent` or deeper belong to this value.
    Returns (value, next_unused_line_index).
    """
    i = _next_nonblank(lines, start)
    if i >= len(lines):
        return None, i

    line = lines[i]
    indent = _indent_of(line)
    stripped = line.strip()

    if indent < base_indent:
        return None, i

    # determine block type from first meaningful line
    if stripped.startswith("- ") or stripped == "-":
        return _parse_list(lines, i, indent)
    elif ":" in stripped:
        return _parse_dict(lines, i, indent)
    else:
        return _parse_scalar(stripped), i + 1


def _parse_list(lines, start, list_indent):
    """Parse a YAML block list. All '- ' items at list_indent belong here."""
    result = []
    i = start

    while i < len(lines):
        i = _next_nonblank(lines, i)
        if i >= len(lines):
            break

        line = lines[i]
        indent = _indent_of(line)
        stripped = line.strip()

        if indent < list_indent:
            break
        if indent > list_indent:
            # shouldn't normally happen; skip
            i += 1
            continue

        if not (stripped.startswith("- ") or stripped == "-"):
            break

        value_part = stripped[2:].strip() if stripped.startswith("- ") else ""
        i += 1

        if not value_part:
            # nested block follows
            j = _next_nonblank(lines, i)
            if j < len(lines) and _indent_of(lines[j]) > list_indent:
                val, i = _parse_value(lines, j, _indent_of(lines[j]))
                result.append(val)
            else:
                result.append(None)
        elif ":" in value_part and not value_part.startswith(('"', "'")):
            # first key of an inline dict
            item_dict = {}
            colon = value_part.index(":")
            k = value_part[:colon].strip()
            v_str = value_part[colon + 1:].strip()

            if v_str and not v_str.startswith("#"):
                item_dict[k] = _parse_scalar(v_str)
            else:
                # value is a sub-block on next lines
                j = _next_nonblank(lines, i)
                if j < len(lines) and _indent_of(lines[j]) > list_indent:
                    sub_val, i = _parse_value(lines, j, _indent_of(lines[j]))
                    item_dict[k] = sub_val
                else:
                    item_dict[k] = None

            # read remaining k:v pairs at indent = list_indent + 2
            item_indent = list_indent + 2
            while i < len(lines):
                j = _next_nonblank(lines, i)
                if j >= len(lines):
                    i = j
                    break
                nl = lines[j]
                ni = _indent_of(nl)
                if ni < item_indent:
                    i = j
                    break
                ns = nl.strip()
                if ":" in ns and not ns.startswith("- "):
                    ci = ns.index(":")
                    nk = ns[:ci].strip()
                    nv = ns[ci + 1:].strip()
                    i = j + 1
                    if nv and not nv.startswith("#"):
                        item_dict[nk] = _parse_scalar(nv)
                    else:
                        # sub-block value
                        k2 = _next_nonblank(lines, i)
                        if k2 < len(lines) and _indent_of(lines[k2]) > ni:
                            sub_val, i = _parse_value(lines, k2, _indent_of(lines[k2]))
                            item_dict[nk] = sub_val
                        else:
                            item_dict[nk] = None
                else:
                    i = j + 1  # skip unexpected line

            result.append(item_dict)
        else:
            result.append(_parse_scalar(value_part))

    return result, i


def _parse_dict(lines, start, dict_indent):
    """Parse a YAML block mapping. All key: lines at dict_indent belong here."""
    result = {}
    i = start

    while i < len(lines):
        i = _next_nonblank(lines, i)
        if i >= len(lines):
            break

        line = lines[i]
        indent = _indent_of(line)
        stripped = line.strip()

        if indent < dict_indent:
            break
        if indent > dict_indent:
            i += 1
            continue
        if stripped.startswith("- ") or stripped == "-":
            break

        if ":" not in stripped:
            i += 1
            continue

        colon = stripped.index(":")
        key = stripped[:colon].strip()
        rest = stripped[colon + 1:].strip()
        i += 1

        if rest and not rest.startswith("#"):
            result[key] = _parse_scalar(rest)
        else:
            # nested block
            j = _next_nonblank(lines, i)
            if j < len(lines) and _indent_of(lines[j]) > dict_indent:
                val, i = _parse_value(lines, j, _indent_of(lines[j]))
                result[key] = val
            else:
                result[key] = None

    return result, i


# ─── DUMPER ────────────────────────────────────────────────────────────────────

def dump(obj, stream=None, default_flow_style=False, sort_keys=True):
    lines = _dump_node(obj, indent=0, sort_keys=sort_keys)
    text = "\n".join(lines) + "\n"
    if stream is not None:
        stream.write(text)
        return None
    return text


def _quote(s):
    if not isinstance(s, str):
        return str(s)
    needs_quote = any(c in s for c in (':', '#', '[', ']', '{', '}', ',', '\n', '"', "'", '!', '&', '*', '?', '|', '<', '>', '=', '%', '@', '`'))
    is_keyword = s in ("true", "false", "null", "yes", "no", "on", "off", "True", "False", "None")
    if needs_quote or is_keyword:
        escaped = s.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _scalar_str(val):
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return str(val)
    if isinstance(val, str):
        return _quote(val)
    return str(val)


def _dump_node(obj, indent, sort_keys):
    pad = " " * indent

    if obj is None or isinstance(obj, (bool, int, float, str)):
        return [_scalar_str(obj)]

    if isinstance(obj, list):
        if not obj:
            return ["[]"]
        lines = []
        for item in obj:
            if isinstance(item, dict):
                keys = sorted(item.keys()) if sort_keys else list(item.keys())
                first = True
                for k in keys:
                    v = item[k]
                    if first:
                        if isinstance(v, (dict, list)) and v:
                            lines.append(f"{pad}- {k}:")
                            lines.extend(_dump_node(v, indent + 4, sort_keys))
                        else:
                            lines.append(f"{pad}- {k}: {_scalar_str(v)}")
                        first = False
                    else:
                        sub_pad = pad + "  "
                        if isinstance(v, (dict, list)) and v:
                            lines.append(f"{sub_pad}{k}:")
                            lines.extend(_dump_node(v, indent + 4, sort_keys))
                        else:
                            lines.append(f"{sub_pad}{k}: {_scalar_str(v)}")
            elif isinstance(item, list):
                sub = _dump_node(item, indent + 2, sort_keys)
                lines.append(f"{pad}-")
                lines.extend(sub)
            else:
                lines.append(f"{pad}- {_scalar_str(item)}")
        return lines

    if isinstance(obj, dict):
        if not obj:
            return ["{}"]
        lines = []
        keys = sorted(obj.keys()) if sort_keys else list(obj.keys())
        for k in keys:
            v = obj[k]
            if isinstance(v, dict):
                lines.append(f"{pad}{k}:")
                lines.extend(_dump_node(v, indent + 2, sort_keys))
            elif isinstance(v, list):
                if not v:
                    lines.append(f"{pad}{k}: []")
                elif all(isinstance(i, (str, int, float, bool)) and i is not None for i in v):
                    items = ", ".join(_scalar_str(i) for i in v)
                    lines.append(f"{pad}{k}: [{items}]")
                else:
                    lines.append(f"{pad}{k}:")
                    lines.extend(_dump_node(v, indent + 2, sort_keys))
            else:
                lines.append(f"{pad}{k}: {_scalar_str(v)}")
        return lines

    return [str(obj)]
