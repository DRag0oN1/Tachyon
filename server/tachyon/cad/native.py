"""Preserve one explicit STEP root; reject ambiguous source selection."""

from ..errors import TachyonError


def import_source(path):
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDocStd import TDocStd_Document

    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise TachyonError("INVALID_STEP", "The STEP reader could not read this document")
    document = TDocStd_Document(TCollection_ExtendedString("Tachyon source inspection"))
    if not reader.Transfer(document):
        raise TachyonError("INVALID_STEP", "The STEP document could not be transferred")
    return _load_source_document(path, document)


def _load_source_document(path, document):
    import cadquery as cq
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.XCAFDoc import XCAFDoc_DocumentTool

    tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots = TDF_LabelSequence()
    tool.GetFreeShapes(roots)
    if roots.Length() != 1:
        raise TachyonError("AMBIGUOUS_STEP_ROOTS", "Supply a STEP with one selected root; multiple or missing roots cannot be silently omitted")
    root = roots.Value(1)
    reference_location = None
    definition = root
    if tool.IsReference_s(root):
        reference_location = cq.Location(tool.GetLocation_s(root))
        definition = TDF_Label()
        if not tool.GetReferredShape_s(root, definition) or definition.IsNull():
            raise TachyonError("INVALID_STEP_REFERENCE", "The source root reference has no component definition")
        if tool.IsReference_s(definition):
            raise TachyonError("INVALID_STEP_REFERENCE", "Nested source-root references require explicit source selection")
    if tool.IsAssembly_s(definition):
        assembly = cq.Assembly.load(str(path), importType="STEP", unit="MM")
        if reference_location is not None:
            # CadQuery classifies the dereferenced definition; retain the original
            # instance's placement instead of flattening it through a part reader.
            assembly.loc = reference_location * assembly.loc
        return assembly
    name = TDataStd_Name()
    source_name = "native_part"
    if root.FindAttribute(TDataStd_Name.GetID_s(), name):
        source_name = name.Get().ToExtString() or source_name
    shape = cq.importers.importStep(str(path), unit="MM")
    return cq.Assembly(shape, name=source_name)
