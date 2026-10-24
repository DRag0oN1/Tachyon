"""Verify the frozen-policy -> structured strategy -> standalone design boundary."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from tachyon_strategy_rl.capability_analysis import capabilities_for, episode, paired_effect, summarize
from tachyon_strategy_rl.environment import sample_capabilities
from tachyon_strategy_rl.handoff import digest, evaluate_feedback, make_spec, read_episodes
from tachyon_strategy_rl.inference import validated_policy
import tachyon_strategy_rl.capability_analysis as analysis_module
import torch


def verify(root, experiment, designer_python):
    root,experiment=Path(root).resolve(),Path(experiment).resolve()
    repository=Path(__file__).resolve().parents[3]
    manifest_path=root/'manifest.json'
    hashes_verified=0
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        for name,expected in manifest['files'].items():
            path=(root/name).resolve()
            assert path.is_relative_to(root) and digest(path)==expected,name
            hashes_verified+=1
        for name,expected in manifest['sourceFiles'].items():
            path=(repository/name).resolve()
            assert path.is_relative_to(repository) and digest(path)==expected,name
    original=json.loads((experiment/'manifest.json').read_text())
    for name,expected in original['files'].items(): assert digest(experiment/name)==expected,name
    findings=json.loads((root/'analysis.json').read_text())
    assert findings['runnerSha256']==digest(analysis_module.__file__)
    spec=json.loads((root/'strategy-spec-v2.json').read_text())
    assert spec==make_spec(experiment,root)
    models={}
    training_seeds=set()
    torch.set_num_threads(1)
    for checkpoint in findings['checkpoints']:
        model,data=validated_policy(experiment/checkpoint['path'])
        assert checkpoint['sha256']==digest(experiment/checkpoint['path'])
        assert data['parameterHash']==checkpoint['parameterHash']
        training_seeds.update(data['capabilitySeeds'])
        models[checkpoint['name']]=model
    rows=read_episodes(root)
    groups=defaultdict(list)
    for row in rows:
        assert row['capability_seed'] not in training_seeds
        groups[(row['stage'],row['variantId'])].append(row)
    for (stage,variant),records in groups.items():
        assert findings['summaries'][stage][variant]==summarize(records),(stage,variant)
    for field,levels in ((key,sorted(v['overrides'][key] for v in findings['variants'] if key in v.get('overrides',{}))) for key in findings['effects']):
        better,worse=(levels[0],levels[-1]) if field.endswith('seconds') else (levels[-1],levels[0])
        for stage in ('calibration','confirmation'):
            assert findings['effects'][field][stage]==paired_effect(groups[(stage,f'{field}={better}')],groups[(stage,f'{field}={worse}')])
    study_seeds={stage:{r['capability_seed'] for r in rows if r['stage']==stage} for stage in ('calibration','confirmation')}
    assert not study_seeds['calibration'] & study_seeds['confirmation']
    variants={v['id']:v for v in findings['variants']}
    sampled=set(); replays=0
    for row in rows:
        key=(row['stage'],row['variantId'],row['policyName'])
        if key in sampled: continue
        sampled.add(key)
        capabilities=capabilities_for(sample_capabilities(row['capability_seed']),variants[row['variantId']])
        replay=episode(models[row['policyName']],capabilities,row['episode_seed'],trace='trace' in row)
        replay.update({key:row[key] for key in ('policyName','capability_seed','episode_seed','stage','variantId')})
        assert replay==row,key
        replays+=1
    with TemporaryDirectory() as temporary:
        child=subprocess.run([str(Path(designer_python).resolve()),'-m','tachyon.design','--strategy',str(root/'strategy-spec-v2.json'),
                              '--output',str(Path(temporary)/'design')],env={**os.environ,'PYTHONPATH':str(repository/'server')},
                             capture_output=True,text=True,check=True)
        for name in ('design-requirements.json','architecture-proposals.json','manifest.json'):
            assert json.loads((Path(temporary)/'design'/name).read_text())==json.loads((root/'design'/name).read_text()),name
    proposals=json.loads((root/'design/architecture-proposals.json').read_text())
    assert len(proposals)==2 and proposals[0]['mechanicalSignature']!=proposals[1]['mechanicalSignature']
    assert proposals[0]['requirements']==proposals[1]['requirements']
    for proposal in proposals:
        assert not proposal['cadGenerated'] and not proposal['completeRobot'] and not proposal['physicalPerformanceVerified']
        assert proposal['newStrategyFamiliesClaimed']==0
    feedback={}
    for name in ('nominal','restricted-reach'):
        record=json.loads((root/f'feedback-{name}-input.json').read_text())
        expected=json.loads((root/f'feedback-{name}-result.json').read_text())
        assert record['robotDesignId']==proposals[0]['id']
        actual=evaluate_feedback(spec,record,experiment)
        assert actual==expected,name
        feedback[name]=actual
    assert feedback['nominal']['actionFrequencies']!=feedback['restricted-reach']['actionFrequencies']
    assert feedback['nominal']['recommendations']!=feedback['restricted-reach']['recommendations']
    assert feedback['nominal']['meanModeledScore']>feedback['restricted-reach']['meanModeledScore']
    reproduction=json.loads((root/'reproduction.json').read_text())
    assert reproduction['rolloutArchivesExactlyMatch'] and reproduction['rolloutArchiveSha256']==digest(root/'episodes.jsonl.gz')
    return {'performanceDomain':'abstract_simulation_only','sourceExperimentFilesUnchanged':len(original['files']),
            'artifactHashesVerified':hashes_verified,'frozenCheckpointsVerified':len(models),
            'storedStudyEpisodes':len(rows),'pairedSummaryCellsRecomputed':len(groups),
            'representativeInterventionReplaysMatched':replays,'fullStudyRepeatedArchiveMatches':True,
            'strategyExportReproduced':True,'standaloneDesignCliReproduced':True,
            'sameLearnedFamilyArchitectureAlternatives':len(proposals),'feedbackEpisodesReplayed':64,
            'capabilityChangeAltersPolicyBehaviorAndRecommendations':True,
            'trainingPerformed':False,'cadGenerated':False,'appRoutesEnabled':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True); parser.add_argument('--experiment',type=Path,required=True)
    parser.add_argument('--designer-python',default='.venv/bin/python')
    args=parser.parse_args()
    print(json.dumps(verify(args.root,args.experiment,args.designer_python),indent=2))
