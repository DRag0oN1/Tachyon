#!/usr/bin/env python3
"""Build a separate generated-robot workspace from original development CAD.

No manufacturer geometry, private project, existing CAD catalog or rights record
is read. This exercises the production STEP/catalog/recipe/viewer pipeline with
explicitly non-VEX parts. It cannot satisfy authentic-VEX robot acceptance.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'server')]


def seed(data_dir, *, handling=True):
    from tachyon.config import Settings
    from tachyon.cad.catalog import Catalog,write_json
    from tachyon.cad.native import import_source
    from tachyon.cad.metrology import measure_definition
    from tachyon.cad.prepare import prepare_components
    from tachyon.models import CatalogManifest,ComponentInput,InterfacePort
    from tachyon.robots.source_pack import MeasuredPart,SourcePack
    from tachyon.robots.architecture_a import compile_architecture_a
    from tachyon import realization as R,strategy_runtime as SR,assemblies as A
    from tools.verification.development_parts import create_parts
    from tools.prepare_architecture_a import PURPOSES,_recipe

    settings=Settings(ROOT,Path(data_dir))
    if settings.data_dir.exists() and any(settings.data_dir.iterdir()):
        raise FileExistsError('Choose a new empty private development workspace; existing work was retained')
    settings.data_dir.mkdir(parents=True)
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    sources=create_parts()
    if handling:
        from tachyon.robots.cup_handling import development_parts
        sources.update(development_parts())
    parts={};rows=[];rights=[]
    for alias,assembly in sources.items():
        identity='dev_'+alias
        source=settings.data_dir/'sources'/f'{identity}.step'
        source.parent.mkdir(exist_ok=True)
        assembly.export(str(source),exportType='STEP')
        source_hash=sha(source)
        evidence=settings.data_dir/'evidence'/f'{identity}.txt'
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text(f'Original Tachyon development CAD; NOT authentic VEX geometry.\nSource SHA-256: {source_hash}\n'
            'Newly authored by this project in development_parts.py/cup_handling.py.\n'
            'No manufacturer/user CAD geometry or private robotics implementation incorporated.\n'
            'Authorized operations: storage, conversion, assembly placement, authenticated local display.\n'
            'This records authorship and local development use, not manufacturing validation or third-party permissions.\n')
        permission=dict(status='qualified',basis='self_authored',rightsholder='Tachyon development CAD authors',
            evidencePath=str(evidence.relative_to(settings.data_dir)),evidenceSha256=sha(evidence),
            reviewedBy='Tachyon original-development generator',reviewedOn=date.today().isoformat())
        rights.append(dict(sourceSha256=source_hash,attribution='Independently authored Tachyon development CAD; not VEX manufacturer CAD',
            operations={op:permission for op in ('acquisition_storage','conversion','assembly_placement','loopback_display')}))
        imported=import_source(source)
        shape=imported.toCompound()
        if not shape.isValid() or not shape.Solids():
            raise ValueError(f'Original development component is not valid solid CAD: {alias}')
        measurements=measure_definition(imported)
        part=MeasuredPart(identity,'authored-'+alias,'Original development '+alias,source_hash,
            PURPOSES.get(alias,'structure'),measurements)
        parts[alias]=part
        rows.append((identity,alias,source,source_hash,measurements))
        print('Authored/measured '+alias,flush=True)
    for alias,canonical in (('bolt','bolt_short'),('brace','spacer')):
        if alias not in parts:parts[alias]=parts[canonical]
    proposal=json.loads((ROOT/SR.PROPOSALS).read_text())[0]
    context=R.architecture_context(ROOT,proposal['id'])
    pack=SourcePack(parts)
    builder,facts=compile_architecture_a(context.proposal,pack)
    facts['robot']=None  # Original development parts never imply authentic-VEX qualification.
    facts['gripper']['interfaceStatus']='Original Tachyon development tool; non-VEX, static Pin retention and physical operation unverified'
    if handling:
        from tachyon.robots.cup_handling import add_cup_handling
        facts['handling']=add_cup_handling(builder,pack,facts)
    inputs=[]
    for identity,alias,source,source_hash,measurements in rows:
        part=parts[alias]
        inputs.append(ComponentInput(id=identity,name='Original development '+alias.replace('_',' ')+' [non-VEX]',
            sku=None,origin_kind='tachyon_authored',geometry_class='test_fixture',source_path=str(source.relative_to(settings.data_dir)),
            source_url='urn:tachyon:independently-authored-development-cad',source_sha256=source_hash,
            expected_bounds_mm=dict(min=measurements['boundsMm'][0],max=measurements['boundsMm'][1]),
            ports=[InterfacePort(id=p.id,kind=p.kind,position_m=p.frame.point(),axis=p.frame.matrix[8:11],evidence=p.evidence) for p in part.ports.values()]))
    write_json(settings.data_dir/'catalog/manifest.json',CatalogManifest(components=inputs).json_data())
    write_json(settings.data_dir/'catalog/rights.json',dict(schemaVersion=1,records=rights))
    catalog=Catalog(settings);catalog.register()
    definitions={c.id:c for c in inputs}
    for part in parts.values():part.catalog_fingerprint=catalog.fingerprint(definitions[part.component_id])
    for alias,part in builder.parts.items():
        builder.parts[alias]=replace(part,catalog_fingerprint=catalog.fingerprint(definitions[part.component_id]))
    recipe=_recipe(builder,facts,pack)
    write_json(settings.data_dir/'catalog/assembly-recipes.json',dict(schemaVersion=1,recipes=[recipe.json_data()]),compact=True)
    print(f'Compiled {len(recipe.template.instances)} placements; preparing original STEP assets',flush=True)
    prepare_components(catalog,inputs)
    service,public=R.qualified_catalog(settings,recipe)
    R._check_actions(context,recipe)
    evidence=dict(provenance='independently_authored_development_CAD_not_VEX',requestedInstances=len(recipe.template.instances),
        resolvedDefinitions=len(public),relationships=len(recipe.template.relationships),subsystems=[s.id for s in recipe.template.subsystems],
        completeAuthenticVexRobot=False,physicalPerformanceVerified=False,configurations={})
    for configuration in recipe.configurations:
        revision=R.build_pose(service,recipe,'development-seed-probe',configuration)
        links=R._links(context,recipe,revision)
        evidence['configurations'][configuration]=dict(graphValid=service.validate(revision).graph_valid,
            instances=len(revision.assembly.instances),bindings=len(links.actions),reach=R._reach(recipe,revision,links))
    evidence['editQualification']=R.edit_qualification(service,context,recipe,'development-seed-probe')
    write_json(settings.data_dir/'generation-evidence.json',evidence)
    write_json(settings.data_dir/'generation-facts.json',facts)
    write_json(settings.data_dir/'measured-pack.json',dict(parts={alias:dict(componentId=p.component_id,sourceSha256=p.source_sha256,
        catalogFingerprint=p.catalog_fingerprint,ports=[x.json_data() for x in p.ports.values()]) for alias,p in parts.items()}))
    print(json.dumps(evidence,default=str),flush=True)
    return settings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'.local/generated-development')
    parser.add_argument('--baseline-only',action='store_true')
    args=parser.parse_args()
    seed(args.data_dir,handling=not args.baseline_only)
