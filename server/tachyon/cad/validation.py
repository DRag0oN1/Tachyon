"""Source-quality diagnostics; an inspectable reference is not a design part."""
def geometry_validation(assembly, shape, *, detailed=True):
    valid = shape.isValid()
    invalid = []
    definitions = {}
    for path, node in (assembly.objects.items() if detailed and not valid else []):
        if node.obj is None:
            continue
        identity = node.metadata.get("definitionLabel", path)
        if identity not in definitions:
            obj = node.obj.val() if hasattr(node.obj, "val") else node.obj
            definitions[identity] = obj.isValid()
        if not definitions[identity]:
            invalid.append({"path": path, "name": node.name,
                            "definitionName": node.metadata.get("definitionName", node.name)})
    return {"status": "valid" if valid else "source_defects", "nativeBrepValid": valid,
            "invalidComponentInstances": invalid, "invalidDefinitionCount": sum(not v for v in definitions.values()) if detailed or valid else None,
            "diagnostics": "aggregate_valid" if valid else "per_definition" if detailed else "aggregate_only",
            "nativeBoundsMaxErrorMm": assembly.metadata.get("nativeBoundsMaxErrorMm"),
            "qualifiedForRobotGeneration": valid,
            "limitations": [] if valid else ["Imported assembly fails the aggregate BRep check; reference inspection only, not qualified engineering geometry"]}
