"""Inspection graph for the imported source; never a complete-robot assertion."""
from ..errors import TachyonError


def source_inspection(component):
    nodes = component["nativeHierarchy"]
    identities = {n["id"] for n in nodes}
    if len(identities) != len(nodes):
        raise TachyonError("INVALID_SOURCE_HIERARCHY", "Imported source contains duplicate node identities")
    relationships = []
    for node in nodes:
        parent = node["parentId"]
        if parent is not None:
            if parent not in identities:
                raise TachyonError("INVALID_SOURCE_HIERARCHY", "Imported source has an unresolved parent")
            relationships.append({"kind": "native_parent", "parentId": parent, "childId": node["id"],
                                  "evidence": "Imported STEP hierarchy; not a verified mechanical mate"})
    return {"kind": "imported_source", "componentId": component["id"],
            "sourceSha256": component["sourceSha256"], "meshSha256": component["meshSha256"],
            "nodes": nodes, "relationships": relationships, "ports": component["ports"],
            "joints": [], "completeRobot": False,
            "limitations": ["Source inspection is not a generated robot", "Mechanical mate and joint qualification remain separate"]}
