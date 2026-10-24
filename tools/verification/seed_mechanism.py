#!/usr/bin/env python3
"""Author a separate non-VEX STEP guide/carriage/tool verification workspace.

This is an original kinematic endpoint fixture, not a competition robot, VEX
component library, powered mechanism qualification or physical-performance proof.
Never reads or modifies user/manufacturer CAD or the default local workspace.
"""
from __future__ import annotations
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'server'))


def seed(data_dir: Path):
    from tachyon.config import Settings
    from tachyon.cad.catalog import Catalog, write_json
    from tachyon.cad.prepare import prepare_component
    from tachyon import assemblies as A
    import cadquery as cq

    settings=Settings(ROOT,data_dir)
    if settings.data_dir.exists() and any(settings.data_dir.iterdir()):
        raise FileExistsError('Use a new empty private workspace')
    settings.data_dir.mkdir(parents=True)
    # Original dimensions in native millimetres/Z-up, never manufacturer parts.
    base=cq.Workplane('XY').box(100,60,8,centered=(True,True,False))
    for x in (-25,25):
        base=base.union(cq.Workplane('XY').box(5,8,260,centered=(True,True,False)).translate((x,0,8)))
    carriage=cq.Workplane('XY').box(70,8,8,centered=True).translate((0,12,0))
    for x in (-25,25):
        guide=cq.Workplane('XY').box(12,16,20).cut(cq.Workplane('XY').box(5.5,8.5,24))
        carriage=carriage.union(guide.translate((x,0,0)))
    tool=cq.Workplane('XY').box(20,90,8,centered=(True,False,True))
    for x in (-12,12):
        tool=tool.union(cq.Workplane('XY').box(8,24,28).translate((x,84,10)))
    definitions=[('fixture_guide','Original guide support',base,[('slide','prismatic',[0,.06,0],[0,1,0])]),
                 ('fixture_carriage','Original sliding carriage',carriage,[('slide','prismatic',[0,0,0],[0,1,0]),('tool','mount',[0,0,-.012],[0,0,1])]),
                 ('fixture_tool','Original tool bracket',tool,[('mount','mount',[0,0,0],[0,0,1])])]
    components=[]; rights=[]; frames={}
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for identity,name,solid,ports in definitions:
        source=settings.data_dir/'sources'/f'{identity}.step'; source.parent.mkdir(parents=True,exist_ok=True)
        assembly=cq.Assembly(name=identity)
        assembly.add(solid,name=identity+'_solid',color=cq.Color(.18,.52,.73) if identity!='fixture_tool' else cq.Color(.92,.47,.17))
        assembly.export(str(source),exportType='STEP')
        imported=cq.Assembly.load(str(source)).toCompound(); bounds=imported.BoundingBox()
        assert imported.isValid()
        source_hash=sha(source)
        evidence=settings.data_dir/'evidence'/f'{identity}-authorship.txt'; evidence.parent.mkdir(parents=True,exist_ok=True)
        evidence.write_text(f'Original Tachyon non-VEX kinematic verification geometry.\nSource SHA-256: {source_hash}\n'
                            'Authored by this project fixture generator; no manufacturer or user CAD incorporated.\n'
                            'Permission: local storage, conversion, assembly placement and loopback display only.\n'
                            'Not a complete robot, VEX component, powered mechanism or physical task validation.\n')
        permission={'status':'qualified','basis':'self_authored','rightsholder':'Tachyon fixture authors',
                    'evidencePath':str(evidence.relative_to(settings.data_dir)),'evidenceSha256':sha(evidence),
                    'reviewedBy':'Original fixture generator (authorship only)','reviewedOn':date.today().isoformat()}
        rights.append({'sourceSha256':source_hash,'attribution':'Original Tachyon non-VEX endpoint fixture; not a robot',
                       'operations':{k:permission for k in ('acquisition_storage','conversion','assembly_placement','loopback_display')}})
        components.append({'id':identity,'name':name+' [test_fixture, non-VEX]','sku':None,
                           'originKind':'tachyon_authored','geometryClass':'test_fixture','sourcePath':str(source.relative_to(settings.data_dir)),
                           'sourceUrl':'https://tachyon.invalid/original-verification-fixture','sourceSha256':source_hash,
                           'expectedBoundsMm':{'min':[bounds.xmin,bounds.ymin,bounds.zmin],'max':[bounds.xmax,bounds.ymax,bounds.zmax]},
                           'ports':[{'id':key,'kind':kind,'positionM':point,'axis':axis,
                                     'evidence':'Original CAD joint reference in converted metres/Y-up; not a verified physical mate'} for key,kind,point,axis in ports]})
        frames[identity]={'sourceSha256':source_hash,'ports':[]}
        for key,kind,point,axis in ports:
            rotation=A.RigidTransform.rotation((1,0,0),-3.141592653589793/2) if axis==[0,1,0] else A.RigidTransform()
            frames[identity]['ports'].append({'id':key,'kind':kind,'frame':A.RigidTransform.translation(*point).compose(rotation).json_data(),
                                                'frameBasis':'measured','evidence':'Authored fixture reference frame; computational endpoint check only'})
    write_json(settings.data_dir/'catalog/manifest.json',{'schemaVersion':1,'components':components})
    write_json(settings.data_dir/'catalog/rights.json',{'schemaVersion':1,'records':rights})
    catalog=Catalog(settings); catalog.register()
    for component in catalog.manifest.components: prepare_component(catalog,component)
    recipe={'id':'original-guided-carriage-endpoint-fixture','alternative':'B',
            'roleComponentIds':{'chassis':['fixture_guide'],'scorer':['fixture_carriage','fixture_tool']},'portFrames':frames,
            'template':{'rootInstanceId':'support','subsystems':[{'id':'chassis','name':'Original guide support'},{'id':'scorer','name':'Original moving fixture tool'}],
                        'instances':[{'id':'support','componentId':'fixture_guide','subsystemId':'chassis'},
                                     {'id':'carrier','componentId':'fixture_carriage','subsystemId':'scorer','parentId':'support'},
                                     {'id':'tool','componentId':'fixture_tool','subsystemId':'scorer','parentId':'carrier'}],
                        'relationships':[{'id':'lift','parentInstanceId':'support','parentPortId':'slide','childInstanceId':'carrier','childPortId':'slide',
                                          'kind':'prismatic','axis':[0,0,1],'limits':[0,.16],'movingMemberIds':['carrier','tool']},
                                         {'id':'tool-mount','parentInstanceId':'carrier','parentPortId':'tool','childInstanceId':'tool','childPortId':'mount'}]},
            'actions':[{'actionId':'place_alliance','subsystemId':'scorer','instanceIds':['carrier','tool'],'jointIds':['lift'],
                        'anchors':[{'id':'fixture-tip','instanceId':'tool','localPointM':[0,.02,-.09]}]}],
            'configurations':{key:{'jointPositions':{'lift':position},'reach':{'actionId':'place_alliance','anchorId':'fixture-tip',
                                                                           'worldPointM':[0,.08+position,-.102],
                                                                           'evidence':'Derived original fixture endpoint; physical scoring support unverified'}}
                              for key,position in (('lower',0.),('raised',.10))}}
    write_json(settings.data_dir/'catalog/assembly-recipes.json',{'schemaVersion':1,'recipes':[recipe]})
    return settings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'.local/mechanism-verification')
    args=parser.parse_args()
    seed(args.data_dir)
    print('Original non-VEX endpoint fixture prepared in a separate private workspace. No robot-readiness claim.')
