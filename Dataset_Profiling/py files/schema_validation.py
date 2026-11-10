"""validate(instance, schema) -> list of (path, message) problems. Empty list = valid.

A small built-in validator, so the module behaves identically on every machine (same error
fields, same messages). It supports exactly the keywords used by our two schema files:
$ref (local), type, const, enum, required, properties, additionalProperties, items,
minimum, maximum, minLength, minItems, maxItems, oneOf, allOf, if/then/else.

cross_check() runs the standard `jsonschema` package, when installed, as an independent
second opinion. It is used by the tests only.
"""
try:  # optional
    import jsonschema
except ImportError:
    jsonschema = None


def _type_ok(value, name):
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "string":
        return isinstance(value, str)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    raise ValueError(f"unsupported type keyword: {name}")


def _resolve(ref, root):
    node = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def _check(value, schema, root, path, out):
    if "$ref" in schema:
        _check(value, _resolve(schema["$ref"], root), root, path, out)
        return
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, t) for t in types):
            out.append((path, f"expected type {types}, got {type(value).__name__}"))
            return
    if "const" in schema and value != schema["const"]:
        out.append((path, f"must equal {schema['const']!r}"))
    if "enum" in schema and value not in schema["enum"]:
        out.append((path, f"must be one of {schema['enum']}"))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append((path, f"must be >= {schema['minimum']}"))
        if "maximum" in schema and value > schema["maximum"]:
            out.append((path, f"must be <= {schema['maximum']}"))
    if isinstance(value, str) and "minLength" in schema and len(value) < schema["minLength"]:
        out.append((path, f"must have at least {schema['minLength']} character(s)"))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                out.append((path, f"missing required field '{key}'"))
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            where = f"{path}.{key}" if path else key
            if key in props:
                _check(item, props[key], root, where, out)
            elif extra is False:
                out.append((where, "field not allowed"))
            elif isinstance(extra, dict):
                _check(item, extra, root, where, out)
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            out.append((path, f"must have at least {schema['minItems']} item(s)"))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            out.append((path, f"must have at most {schema['maxItems']} item(s)"))
        if "items" in schema:
            for i, item in enumerate(value):
                _check(item, schema["items"], root, f"{path}[{i}]", out)
    if "oneOf" in schema:
        hits = sum(1 for s in schema["oneOf"] if not _problems(value, s, root, path))
        if hits != 1:
            out.append((path, "does not match exactly one allowed shape"))
    for sub in schema.get("allOf", []):
        _check(value, sub, root, path, out)
    if "if" in schema:
        branch = "then" if not _problems(value, schema["if"], root, path) else "else"
        if branch in schema:
            _check(value, schema[branch], root, path, out)


def _problems(value, schema, root, path):
    found = []
    _check(value, schema, root, path, found)
    return found


def validate(instance, schema):
    return _problems(instance, schema, schema, "")


def cross_check(instance, schema):
    """Messages from the standard jsonschema package, or None if it is not installed."""
    if jsonschema is None:
        return None
    return [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(instance)]


def schema_is_valid(schema):
    """True/False from the standard package's own schema check, or None if not installed."""
    if jsonschema is None:
        return None
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        return True
    except jsonschema.SchemaError:
        return False
