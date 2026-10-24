"""Preserve one explicit STEP root; reject ambiguous source selection."""

from ..errors import TachyonError


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
            node = cq.Assembly(name=name, loc=occurrence_location * cq.Location(tool.GetLocation_s(definition)), color=color, metadata=metadata)
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
