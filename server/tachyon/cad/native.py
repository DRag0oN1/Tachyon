"""Preserve one explicit STEP root; reject ambiguous source selection."""

from copy import deepcopy

from ..errors import TachyonError
from ..models import SourceSelection


def select_source_definition(assembly, selection: SourceSelection):
    """Copy one definition tree in its native frame, retaining the original BReps.

    Multiple occurrences of the same definition are one selection. Occurrence
    and ancestor placements are deliberately excluded; the definition's own
    shape (including any intrinsic location) remains unchanged. Subassembly
    children keep their native hierarchy, locations and definition metadata.
    They are never flattened into a replacement part BRep.
    """
    import cadquery as cq

    matches = [node for node in assembly.objects.values()
               if (selection.source_label is None or node.metadata.get("sourceLabel") == selection.source_label)
               and (selection.definition_label is None or node.metadata.get("definitionLabel") == selection.definition_label)]
    if not matches:
        raise TachyonError("SOURCE_SELECTION_NOT_FOUND", "No native definition matches the registered source selection")
    identities = {node.metadata.get("definitionLabel") for node in matches}
    if len(identities) != 1 or None in identities:
        raise TachyonError("AMBIGUOUS_SOURCE_SELECTION", "The source selection does not identify exactly one native definition")
    if any(node.metadata.get("definitionName") != selection.expected_definition_name for node in matches):
        raise TachyonError("SOURCE_SELECTION_MISMATCH", "The selected native definition name changed")
    if any(not node.children and node.obj is None for node in matches):
        raise TachyonError("INVALID_SOURCE_SELECTION", "The selected native definition has no geometry or children")

    def definition_location(node):
        if node.obj is not None:
            # Leaf intrinsic location is already part of its BRep, while loc
            # carries only the occurrence placement.
            return cq.Location()
        from OCP.gp import gp_Trsf
        values = node.metadata.get("definitionLocation")
        if values is None:
            raise TachyonError("INVALID_SOURCE_SELECTION", "The native subassembly definition frame is missing")
        transform = gp_Trsf()
        transform.SetValues(*values)
        return cq.Location(transform)

    def same_location(left, right):
        a, b = left.wrapped.Transformation(), right.wrapped.Transformation()
        return all(abs(a.Value(i, j) - b.Value(i, j)) < 1e-10
                   for i in range(1, 4) for j in range(1, 5))

    def same_definition(left, right, *, root=True):
        if (left.obj is None) != (right.obj is None) or len(left.children) != len(right.children):
            return False
        if any(left.metadata.get(key) != right.metadata.get(key)
               for key in ("definitionLabel", "definitionName")):
            return False
        if not same_location(definition_location(left) if root else left.loc,
                             definition_location(right) if root else right.loc):
            return False
        if left.obj is not None:
            a = left.obj.val() if hasattr(left.obj, "val") else left.obj
            b = right.obj.val() if hasattr(right.obj, "val") else right.obj
            if not a.isEqual(b):
                return False
        return all(same_definition(a, b, root=False) for a, b in zip(left.children, right.children))

    node = matches[0]
    for other in matches[1:]:
        if not same_definition(node, other):
            raise TachyonError("AMBIGUOUS_SOURCE_SELECTION", "Occurrences disagree about the selected native definition geometry")
    selected = cq.Assembly(node.obj, loc=definition_location(node),
                           name=selection.expected_definition_name,
                           color=node.color, metadata=deepcopy(node.metadata))
    for child in node.children:
        selected.add(child)
    # CadQuery copies nodes/locations but shares metadata. Detach nested frame
    # data too, while leaving the source BReps unmodified.
    for child in selected.objects.values():
        child.metadata = deepcopy(child.metadata)
    return selected


def import_source(path):
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDocStd import TDocStd_Document
    from OCP.Interface import Interface_Static

    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(True)
    reader.SetLayerMode(True)
    Interface_Static.SetCVal_s("xstep.cascade.unit", "MM")
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise TachyonError("INVALID_STEP", "The STEP reader could not read this document")
    document = TDocStd_Document(TCollection_ExtendedString("Tachyon source inspection"))
    if not reader.Transfer(document):
        raise TachyonError("INVALID_STEP", "The STEP document could not be transferred")
    return _load_source_document(path, document)


def _load_source_document(path, document):
    import cadquery as cq
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence, TDF_Tool
    from OCP.TCollection import TCollection_AsciiString
    from cadquery.occ_impl.importers.assembly import _get_name, _get_ref_color, _get_shape_color
    from OCP.XCAFDoc import XCAFDoc_DocumentTool

    tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots = TDF_LabelSequence()
    tool.GetFreeShapes(roots)
    if roots.Length() != 1:
        raise TachyonError("AMBIGUOUS_STEP_ROOTS", "Supply a STEP with one selected root; multiple or missing roots cannot be silently omitted")
    root = roots.Value(1)
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(document.Main())
    count = 0

    def entry(label):
        value = TCollection_AsciiString()
        TDF_Tool.Entry_s(label, value)
        return value.ToCString()

    def visit(label, active=frozenset(), depth=0):
        nonlocal count
        count += 1
        if count > 100000 or depth > 100:
            raise TachyonError("STEP_HIERARCHY_LIMIT", "The source hierarchy exceeds the bounded importer limits")
        definition = label
        occurrence_location = cq.Location()
        if tool.IsReference_s(label):
            occurrence_location = cq.Location(tool.GetLocation_s(label))
            definition = TDF_Label()
            if not tool.GetReferredShape_s(label, definition) or definition.IsNull() or tool.IsReference_s(definition):
                raise TachyonError("INVALID_STEP_REFERENCE", "A source reference has no directly resolvable definition")
        identity = entry(definition)
        if identity in active:
            raise TachyonError("CYCLIC_STEP_HIERARCHY", "The source contains a cyclic assembly reference")
        occurrence_name, definition_name = _get_name(label), _get_name(definition)
        name = ((definition_name if tool.IsAssembly_s(definition) else occurrence_name)
                or definition_name or ("native_" + entry(label)))
        color = _get_ref_color(label) or _get_ref_color(definition)
        metadata = {"sourceLabel": entry(label), "definitionLabel": identity,
                    "sourceName": name, "occurrenceName": occurrence_name,
                    "definitionName": definition_name}
        if tool.IsAssembly_s(definition):
            definition_location = cq.Location(tool.GetLocation_s(definition))
            transform = definition_location.wrapped.Transformation()
            metadata["definitionLocation"] = [transform.Value(i, j)
                                              for i in range(1, 4) for j in range(1, 5)]
            node = cq.Assembly(name=name, loc=occurrence_location * definition_location, color=color, metadata=metadata)
            labels = TDF_LabelSequence()
            tool.GetComponents_s(definition, labels)
            # Index native sequences explicitly. CadQuery's face-metadata iterator
            # is pathological on the manufacturer's deeply labeled STEP files.
            for i in range(1, labels.Length() + 1):
                child = visit(labels.Value(i), active | {identity}, depth + 1)
                unique = child.name
                if unique in node.objects:
                    unique += "__occurrence_" + child.metadata["sourceLabel"].replace(":", "_")
                node.add(child, name=unique)
            return node
        shape = tool.GetShape_s(definition)
        if shape.IsNull():
            raise TachyonError("EMPTY_STEP_COMPONENT", "A native component has no geometry")
        return cq.Assembly(cq.Shape.cast(shape), name=name, loc=occurrence_location,
                           color=color or _get_shape_color(shape, color_tool), metadata=metadata)

    assembly = visit(root)
    # Compare against XCAF's own located root, independently of our traversal.
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box

    def bounds(shape):
        box = Bnd_Box()
        # Conservative source/reconstruction comparison, without repeatedly
        # solving expensive exact BSpline extrema. It performs no tessellation.
        BRepBndLib.Add_s(shape, box, False)
        return box.Get()

    source_bounds = bounds(tool.GetShape_s(root))
    rebuilt_bounds = bounds(assembly.toCompound().wrapped)
    error = max(abs(a-b) for a, b in zip(source_bounds, rebuilt_bounds))
    if error > 0.001:
        raise TachyonError("NATIVE_PLACEMENT_MISMATCH", "Imported component placements differ from the native located source root")
    assembly.metadata["nativeBoundsMaxErrorMm"] = error
    return assembly
