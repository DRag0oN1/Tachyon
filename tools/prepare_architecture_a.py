#!/usr/bin/env python3
"""Compile and prepare architecture A in a separate, private local catalog.

Run with the project's .venv. No rights decisions are created or promoted. The
existing native importer, metrology, catalog preparation and realization checks
remain authoritative. This command never calls realize or starts the app.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import importlib
import json
import math
from pathlib import Path
import re
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from tachyon import assemblies as A, realization as R, strategy_runtime as SR
from tachyon.cad import native
from tachyon.cad.catalog import Catalog, PREPARE_OPERATIONS, read_json, write_json
from tachyon.cad.metrology import measure_definition
from tachyon.cad.prepare import prepare_components
from tachyon.cad.rights import sha256_file
from tachyon.config import Settings
from tachyon.errors import TachyonError
from tachyon.models import CatalogManifest, ComponentInput, InterfacePort, PreparedComponent, RightsManifest, SourceSelection
from tachyon.robot_qualification import qualify_robot
from tachyon.robots.source_pack import MeasuredPart, SourcePack as BuildSourcePack


MEASUREMENTS_SOURCE_SHA256 = "d291e70cf6ccd5260983193ab07d9f824b965b1c5f7e2ef298e961e7e7768fb7"
ALIASES = {"channel":2,"short_channel":4,"angle":5,"bearing":10,"shaft_long":16,"shaft_medium":11,
    "shaft_short":25,"gear84":36,"gear12":37,"motor":6,"omni":39,"traction":31,"gripper":45,
    "shaft_insert":30,"collar":29,"bolt_short":20,"bolt_mid":18,"bolt_long":19,"bolt25":28,
    "nut":21,"washer":53,"spacer":23,"brace":23,"standoff":27,"standoff_short":17,"battery_clip":7,"brain":55,"battery":56}
PURPOSES = {"channel":"structure","short_channel":"structure","angle":"structure","bearing":"bearing",
    "shaft_long":"shaft","shaft_medium":"shaft","shaft_short":"shaft","gear84":"gear","gear12":"gear",
    "motor":"motor","omni":"wheel","traction":"wheel","gripper":"gripper","shaft_insert":"coupler",
    "collar":"retainer","bolt_short":"fastener","bolt_mid":"fastener","bolt_long":"fastener","bolt25":"fastener",
    "nut":"fastener","washer":"spacer","spacer":"spacer","brace":"spacer","standoff":"spacer","standoff_short":"spacer","battery_clip":"structure","brain":"control","battery":"power"}
MARKER = ".architecture-a-preparation.json"
OWNER = "tachyon.architecture_a_private_preparation"


def fail(code, message):
    raise TachyonError(code, message)


def _files(directory):
    result = {}
    for path in directory.rglob("*"):
        if path.is_symlink():
            fail("OUTPUT_NOT_OWNED", "Private preparation output must not contain symlinks")
        if path.is_file() and path != directory / MARKER:
            result[path.relative_to(directory).as_posix()] = sha256_file(path)
    return result


def _check_output(source, settings, proposal, component):
    if (settings.root != source.settings.root or settings.cad_dir != source.settings.cad_dir
            or settings.rights_dir != source.settings.rights_dir):
        fail("OUTPUT_ROOT_MISMATCH", "Output must retain the source catalog's project, CAD and rights roots")
    output = settings.data_dir
    if (not output.is_relative_to(settings.root / ".local") or output == source.settings.data_dir
            or source.settings.data_dir.is_relative_to(output)):
        fail("OUTPUT_NOT_PRIVATE", "Choose a separate output directory beneath .local; the source catalog cannot be overwritten")
    expected = {"kind":OWNER,"sourceSha256":component.source_sha256,"architectureId":proposal["id"]}
    if output.exists() and any(output.iterdir()):
        marker = output / MARKER
        try:
            saved = json.loads(marker.read_text())
        except (OSError, ValueError):
            fail("OUTPUT_NOT_OWNED", "Output contains unrelated files; choose a new private data directory")
        if any(saved.get(k) != v for k,v in expected.items()) or saved.get("files") != _files(output):
            fail("OUTPUT_NOT_OWNED", "Output ownership or saved file hashes changed; existing work was preserved")
    return expected


def _child_definitions(selected):
    counts = Counter()
    def visit(node):
        if node.obj is not None:
            counts[(node.metadata["definitionLabel"],node.metadata["definitionName"])] += 1
        for child in node.children:
            visit(child)
    visit(selected)
    return [dict(definitionLabel=label,definitionName=name,quantity=count) for (label,name),count in sorted(counts.items())]


def _measurements(selected, label, cache, *, cached_assemblies=False):
    inventory=_child_definitions(selected)
    if selected.children and cached_assemblies and label in cache and cache[label].get("sourceDefinitions")!=inventory:
        fail("MEASUREMENT_IDENTITY_MISMATCH", "Pinned assembly metrology differs from the native definition inventory")
    if label not in cache or selected.children and not cached_assemblies:
        measured = measure_definition(selected)
    else:
        measured = dict(cache[label])
        if measured.get("name") != selected.metadata["definitionName"]:
            fail("MEASUREMENT_IDENTITY_MISMATCH", "Cached leaf measurements name a different native definition")
    bounds = measured.get("boundsMm")
    if (not isinstance(bounds,list) or len(bounds) != 2 or any(len(p) != 3 for p in bounds)
            or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for p in bounds for v in p)
            or any(a>b for a,b in zip(*bounds))):
        fail("INVALID_MEASUREMENTS", "Source measurements need finite, ordered native millimetre bounds")
    measured["sourceDefinitions"] = inventory
    return measured


def _copy_rights(source, settings, manifest):
    """Copy existing decisions unchanged, relocating only private evidence paths."""
    data = manifest.json_data()
    for record in data["records"]:
        for permission in record["operations"].values():
            value = permission.get("evidencePath")
            if not value:
                continue
            original = source.settings.rights_path(value)
            try:
                settings.rights_path(str(original))
                permission["evidencePath"] = str(original)
            except TachyonError:
                # Evidence inside the original private data directory cannot be
                # referenced through another data root. Copy its exact bytes.
                digest = sha256_file(original)
                target = settings.local_path("catalog/evidence/"+digest+original.suffix, must_exist=False)
                target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists() and sha256_file(target) != digest:
                    fail("OUTPUT_NOT_OWNED", "An evidence copy conflicts with existing private output")
                if not target.exists(): shutil.copyfile(original,target)
                permission["evidencePath"] = str(target.relative_to(settings.data_dir))
    return RightsManifest.model_validate(data)


def _edit_group(builder, facts):
    if facts.get("editGroup") is not None:
        return facts["editGroup"]
    controls = facts.get("fourBar",{}).get("controls",[])
    if not controls:
        return None
    driver,driver_ratio = controls[0]
    if not driver_ratio:
        fail("INVALID_COMPILER_FACTS", "Four-bar driver coupling ratio cannot be zero")
    result = []
    for identity,ratio in controls:
        relative = ratio/driver_ratio
        offset = builder.poses["lower"][identity] - relative*builder.poses["lower"][driver]
        result.append(dict(jointId=identity,ratio=relative,offset=offset))
    compiled = builder.compile(reach=facts["reach"])
    changed = {i for i,q in builder.poses["lower"].items() if abs(q-builder.poses["raised"][i]) > 1e-9}
    members = sorted({member for rel in compiled["template"]["relationships"] if rel["id"] in changed for member in rel.get("movingMemberIds",[])})
    return dict(id="four-bar-and-carried-tool",driverJointId=driver,members=members,coupling=result)


def _oem_inventory(definitions):
    """The bounded Claw Kit v2 inventory; labels/names/counts come from native CAD."""
    result = []
    for definition in definitions:
        item = dict(definition); name = item["definitionName"]
        if name.startswith("276-4840-"): purpose = "motor"
        elif name.startswith("276-6010-011 "): purpose = "gear"; item["teeth"] = 12
        elif name.startswith("276-6010-003 "): purpose = "gear"; item["teeth"] = 35
        elif name.startswith("276-6010-002 "): purpose = "jaw"
        elif name.startswith(("276-499","276-500","276-1028","276-6009-007")): purpose = "fastener"
        elif name.startswith(("276-6010-010 ","228-2500-112 ")): purpose = "spacer"
        elif name.startswith("228-2500-1") and "143" not in name: purpose = "shaft"
        else: purpose = "structure"
        item["purpose"] = purpose; result.append(item)
    return result


def _recipe(builder, facts, pack, receipts=()):
    if not isinstance(facts.get("reach"),dict):
        fail("COMPILER_INCOMPLETE", "Compiler must return explicit lower/raised reach facts")
    robot = facts.get("robot")
    robot = robot.json_data() if hasattr(robot,"json_data") else json.loads(json.dumps(robot)) if robot is not None else None
    if robot is not None:
        by_component = {p.component_id:p for p in pack.parts.values()}
        for item in robot.get("bom",[]):
            part = by_component.get(item["componentId"])
            if part is None or item["catalogFingerprint"] not in ("0"*64,part.catalog_fingerprint):
                fail("STALE_COMPILER_BOM", "Compiler BOM must identify a current measured source part")
            item["catalogFingerprint"] = part.catalog_fingerprint
    gripper = facts.get("gripper",{})
    if robot is not None and gripper.get("instanceId") and "gripper" in pack.parts:
        part = pack.parts["gripper"]
        if part.definition_name.startswith("276-6010-100 "):
            receipt = next((p for p in receipts if p.id==part.component_id),None)
            unit = dict(kind="vex_claw_kit_v2",instanceId=gripper["instanceId"],componentId=part.component_id,
                catalogFingerprint=part.catalog_fingerprint,sourceSha256=part.source_sha256,
                definitionLabel=part.definition_label,definitionName=part.definition_name,
                nativeHierarchySha256=A.content_hash([n.json_data() for n in receipt.native_hierarchy]) if receipt else "0"*64,
                children=_oem_inventory(part.measurements["sourceDefinitions"]),
                evidence="Reviewed factory Claw Kit v2 native definition inventory; internal pose retained; no animation, Pin-fit or physical performance claim")
            robot["integratedUnits"] = [u for u in robot.get("integratedUnits",[]) if u["instanceId"]!=unit["instanceId"]]+[unit]
    raw = builder.compile(reach=facts["reach"],robot=robot,edit_group=_edit_group(builder,facts))
    recipe = R.Recipe.model_validate_json(json.dumps(raw,allow_nan=False),strict=True)
    book = {"schemaVersion":1,"recipes":[recipe.json_data()]}
    # Enforce the same byte/depth/node limits that the runtime will actually load.
    R._bounded_json((json.dumps(book,separators=(",", ":"),sort_keys=True)+"\n").encode())
    return recipe


def _qualification(settings, proposal, recipe):
    result = {"status":"inactive","missing":[],"revisions":{},"reports":{},"reach":{}}
    try:
        context = R.architecture_context(settings.root,proposal["id"])
        if context.proposal != proposal:
            fail("ARCHITECTURE_DATASET_UNVERIFIED", "Compiler proposal differs from the verified architecture handoff")
        service,public = R.qualified_catalog(settings,recipe)
        R._check_actions(context,recipe)
        for configuration in recipe.configurations:
            revision = R.build_pose(service,recipe,A.stable_id("design",proposal["id"],A.content_hash(recipe.json_data())),configuration)
            links = R._links(context,recipe,revision)
            reach = R._reach(recipe,revision,links)
            result["revisions"][configuration] = dict(revisionId=revision.id,engineeringHash=revision.engineering_hash)
            result["reports"][configuration] = qualify_robot(revision,recipe.robot,prepared_components=public).json_data()
            result["reach"][configuration] = reach
        available = max((r["heightM"] for r in result["reach"].values() if r),default=None)
        result["availableEndpointHeightM"] = available
        result["canEdit"],result["editMissing"] = R.edit_qualification(service,context,recipe,revision.assembly.design_id)
        target = context.spec["capabilityRequirements"]["targets"]["reachM"]
        if all(r["completeRobot"] for r in result["reports"].values()) and available is not None and available >= target:
            result["status"] = "qualified_input"
        else:
            result["status"] = "partial_input"
    except R.QualificationBlocked as error:
        result["missing"] = error.reasons
    except TachyonError as error:
        result["missing"] = [dict(role="recipe",code=error.code,message=error.message)]
    return result


def prepare_parts(source_catalog, output_settings, proposal, compiler=None, *, measurements=None, aliases=None, parts_only=False):
    """Prepare owned private inputs; injectable compiler/aliases support small fixtures.

    No realization occurs, including when existing placement rights qualify.
    Existing decisions are copied; their evidence and current scope are rechecked
    by Catalog/RightsPolicy. The main source registration is never changed.
    """
    if compiler is None:
        compiler = getattr(importlib.import_module("tachyon.robots.architecture_a"),"compile_architecture_a",None)
    parts_only = parts_only or not callable(compiler)
    source = next((c for c in source_catalog.manifest.components if c.id=="v5_clawbot_reference"),None)
    if source is None:
        fail("SOURCE_COMPONENT_MISSING", "The source catalog needs v5_clawbot_reference")
    ownership = _check_output(source_catalog,output_settings,proposal,source)
    if parts_only and output_settings.local_path("catalog/assembly-recipes.json",must_exist=False).exists():
        fail("OUTPUT_HAS_RECIPE", "Parts-only preparation cannot replace an existing compiled catalog; use a separate private output")
    original = source_catalog.source(source,PREPARE_OPERATIONS)  # rights BEFORE import
    output_settings.source_path(str(original))  # shared configured CAD root only
    cache = {};cached_assemblies=False
    if measurements is not None and source.source_sha256 == MEASUREMENTS_SOURCE_SHA256:
        path = Path(measurements).expanduser().resolve()
        if not path.is_file() or path.stat().st_size > 64*1024*1024:
            fail("INVALID_MEASUREMENTS", "Explicit leaf metrology is missing or exceeds 64 MiB")
        cache = json.loads(path.read_text())
        if not isinstance(cache,dict): fail("INVALID_MEASUREMENTS", "Expected a native definition measurement mapping")
        if "sourceSha256" in cache:
            if cache["sourceSha256"] != source.source_sha256 or not isinstance(cache.get("definitions"),dict):
                fail("MEASUREMENT_IDENTITY_MISMATCH", "Wrapped metrology must identify these exact original source bytes")
            cache = cache["definitions"];cached_assemblies=True
    imported = native.import_source(original)
    measured, selections, selected_parts = {}, {}, {}
    for alias,number in (aliases or ALIASES).items():
        label = "0:1:1:"+str(number)
        names = {n.metadata.get("definitionName") for n in imported.objects.values() if n.metadata.get("definitionLabel")==label}
        if len(names)!=1 or None in names:
            fail("SOURCE_SELECTION_NOT_FOUND", "A required native source definition is missing or ambiguous: "+alias)
        name = names.pop()
        selection = SourceSelection(definition_label=label,expected_definition_name=name)
        identity = "vex_"+str(number)
        if identity not in selected_parts:
            selected = native.select_source_definition(imported,selection)
            data = _measurements(selected,label,cache,cached_assemblies=cached_assemblies)
            selected_parts[identity] = MeasuredPart(identity,label,name,source.source_sha256,PURPOSES.get(alias,"structure"),data)
        measured[alias] = selected_parts[identity]
        selections[measured[alias].component_id] = selection
    if "bolt_short" in measured: measured["bolt"] = measured["bolt_short"]  # older authoring helper spelling
    pack = BuildSourcePack(measured)
    builder,facts = (None,{}) if parts_only else compiler(proposal,pack)
    if not parts_only and (not isinstance(facts,dict) or not all(k in facts for k in ("reach","gripper","fourBar"))):
        fail("COMPILER_INCOMPLETE", "Compiler must return a RecipeBuilder plus reach, gripper and fourBar facts")
    unique = {p.component_id:p for p in measured.values()}
    inputs = []
    # Fingerprints need every port the compiler collected, not the provisional pack.
    fingerprint_catalog = Catalog(output_settings)
    for identity,part in sorted(unique.items()):
        low,high = part.measurements["boundsMm"]
        sku = re.match(r"(?:276|275|228)-[0-9]+(?:-[0-9]+)*",part.definition_name)
        component = ComponentInput(id=identity,name=part.definition_name,sku=sku.group() if sku else None,
            source_url=source.source_url,source_path=str(original),source_sha256=source.source_sha256,
            origin_kind=source.origin_kind,geometry_class=source.geometry_class,source_selection=selections[identity],
            reference_only=False,expected_bounds_mm=dict(min=low,max=high),
            ports=[InterfacePort(id=p.id,kind=p.kind,position_m=p.frame.point(),axis=p.frame.matrix[8:11],evidence=p.evidence) for p in part.ports.values()])
        part.catalog_fingerprint = fingerprint_catalog.fingerprint(component)
        inputs.append(component)
    for alias,part in (builder.parts.items() if builder else ()):
        if part.component_id not in unique: fail("INVALID_COMPILER_PART", "Compiler referenced a part outside the measured source pack")
        if part.source_sha256 != source.source_sha256 or part.ports != unique[part.component_id].ports:
            fail("INVALID_COMPILER_PART", "Compiler part frames or source identity differ from the shared measured pack")
        builder.parts[alias] = replace(part,catalog_fingerprint=unique[part.component_id].catalog_fingerprint)
    facts = json.loads(json.dumps(facts,allow_nan=False,default=lambda v:v.json_data()))
    if not parts_only:
        _recipe(builder,facts,pack)  # strict schema/size qualification BEFORE saved recipe inputs
    output_settings.data_dir.mkdir(parents=True,exist_ok=True)
    marker = output_settings.data_dir / MARKER
    try:
        rights = _copy_rights(source_catalog,output_settings,RightsManifest(records=list(source_catalog.policy.records.values())))
        write_json(output_settings.local_path("catalog/manifest.json",must_exist=False),CatalogManifest(components=inputs).json_data())
        write_json(output_settings.local_path("catalog/rights.json",must_exist=False),rights.json_data())
        catalog = Catalog(output_settings)
        catalog.register()
        # Existing preparation owns its checked per-source import cache; there
        # is no geometry injection or new CAD engine here.
        preparation_errors=[]
        def record_error(component,error):
            preparation_errors.append(dict(role="component",code=error.code,message=f"{component.id}: {error.message}"))
        receipts = prepare_components(catalog,inputs,reuse_existing=True,on_error=record_error)
        prepared = [PreparedComponent.model_validate(r) for r in receipts]
        recipe = None if parts_only else _recipe(builder,facts,pack,prepared)
        if recipe:
            write_json(output_settings.local_path("catalog/assembly-recipes.json",must_exist=False),dict(schemaVersion=1,recipes=[recipe.json_data()]),compact=True)
            qualification = _qualification(output_settings,proposal,recipe)
            if recipe.robot: facts["robot"] = recipe.robot.json_data()
        else:
            qualification = dict(status="parts_prepared",missing=[],recipeWritten=False,
                placement=catalog.policy.operation_status(source.source_sha256)["assembly_placement"])
        if preparation_errors:
            qualification["status"]="inactive"
            qualification["missing"]=[*preparation_errors,*qualification["missing"]]
        write_json(output_settings.local_path("source_metrology.json",must_exist=False),dict(schemaVersion=1,sourceSha256=source.source_sha256,
            definitions={p.definition_label:p.measurements for p in unique.values()}))
        write_json(output_settings.local_path("measured-pack.json",must_exist=False),dict(sourceSha256=source.source_sha256,
            parts={alias:dict(componentId=p.component_id,definitionLabel=p.definition_label,definitionName=p.definition_name,
                catalogFingerprint=p.catalog_fingerprint,purpose=p.purpose,measurements=p.measurements,
                ports=[port.json_data() for port in p.ports.values()]) for alias,p in measured.items()}))
        write_json(output_settings.local_path("configuration.json",must_exist=False),dict(architectureId=proposal["id"],
            recipeHash=A.content_hash(recipe.json_data()) if recipe else None,facts=facts))
        write_json(output_settings.local_path("qualification.json",must_exist=False),qualification)
        return dict(dataDir=str(output_settings.data_dir),components=len(receipts),registeredComponents=len(inputs),recipeId=recipe.id if recipe else None,
            recipeHash=A.content_hash(recipe.json_data()) if recipe else None,**qualification)
    finally:
        write_json(marker,{**ownership,"files":_files(output_settings.data_dir)})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir",type=Path,default=ROOT/".local/robot-generated")
    parser.add_argument("--source-data-dir",type=Path)
    parser.add_argument("--measurements",type=Path,help="Explicitly reuse pinned-source leaf metrology; assemblies are measured fresh")
    parser.add_argument("--rights",help="Existing approved manifest, resolved through the configured rights root (e.g. rights:approved.json)")
    parser.add_argument("--architecture-id")
    parser.add_argument("--parts-only",action="store_true",help="Prepare selected source parts without calling a robot compiler or writing a recipe")
    args = parser.parse_args(argv)
    try:
        base = Settings.environment()
        source_settings = replace(base,data_dir=args.source_data_dir.resolve()) if args.source_data_dir else base
        rights = source_settings.rights_path(args.rights) if args.rights else None
        source = Catalog(source_settings,rights_path=rights)
        output = Settings(source_settings.root,args.data_dir.resolve(),source_settings.ui_origin,source_settings.cad_dir,source_settings.rights_dir)
        architecture_id = args.architecture_id
        if architecture_id is None:
            proposals = json.loads((source_settings.root/SR.PROPOSALS).read_text())
            architecture_id = next(p["id"] for p in proposals if p["alternative"]=="A")
        context = R.architecture_context(source_settings.root,architecture_id)
        if context.proposal["alternative"] != "A": fail("UNSUPPORTED_ROBOT_RECIPE", "Choose architecture A")
        result = prepare_parts(source,output,context.proposal,measurements=args.measurements,parts_only=args.parts_only)
        print(f"Prepared {result['components']} source-selected catalog components: {result['status']}.")
        if result["recipeId"]:
            print(f"Recipe: {result['recipeId']}.")
        else:
            print("No robot recipe was written. Rerun without --parts-only when compile_architecture_a is available.")
        for reason in result["missing"]: print(f"{reason['code']}: {reason['message']}")
        relative = output.data_dir.relative_to(output.root)
        print(f"Private output: {relative}. Source catalog and originals were retained.")
        print(f"Launch: TACHYON_DATA_DIR={shlex.quote(str(relative))} PYTHONPATH=server .venv/bin/python -m uvicorn tachyon.app:app --host 127.0.0.1 --port 8000")
        print("The tool does not realize designs. Placement still requires current qualified assembly rights.")
        return 0
    except (TachyonError,OSError,ValueError,TypeError,AttributeError,KeyError,StopIteration) as error:
        code = getattr(error,"code","PREPARATION_FAILED")
        message = error.message if isinstance(error,TachyonError) else "Private preparation inputs or compiler output failed validation; existing files were retained"
        print(f"{code}: {message}",file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
