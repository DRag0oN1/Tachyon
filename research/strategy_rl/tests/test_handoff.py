from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pytest

from tachyon_strategy_rl.environment import Env
from tachyon_strategy_rl.handoff import FrozenStrategyController, evaluate_feedback, make_spec, strategy_identity
from tachyon_strategy_rl.inference import PolicyInference


ROOT = Path(__file__).parents[1]/"results/override-ppo-v1"
BRIDGE = Path(__file__).parents[1]/"results/strategy-design-bridge-v1"


@pytest.fixture
def spec():
    return json.loads((BRIDGE/"strategy-spec-v2.json").read_text())


def feedback_record(spec):
    targets=spec['capabilityRequirements']['targets']
    keys=('driveSpeedMps','reachM','acquisitionSeconds','placementSeconds',
          'acquisitionSuccessProbability','placementSuccessProbability','turnSeconds')
    return {'schemaVersion':2,'strategySpecId':spec['id'],'robotDesignId':'synthetic-contract-design',
            'designRevisionId':'design-spec-revision-1','environmentId':spec['competition']['environmentId'],
            'source':'predicted','method':'Illustrative contract-test estimates, not CAD-derived',
            'evidenceReference':'test_fixture','testConditions':'Nominal, no physical measurements',
            'units':'SI_seconds_metres_probabilities','capabilities':{k:targets[k] for k in keys},
            'uncertainty':{k:.01 for k in keys}}


def test_controller_keeps_conditional_neural_actions_instead_of_replaying_sequence(spec):
    controller=FrozenStrategyController(spec,ROOT)
    original=PolicyInference(ROOT/'runs/seed-17/checkpoint.pt')
    env=Env(seed=82); actions=set()
    observation=env.observe()
    while not env.done:
        mask=env.action_mask()
        actual=controller.act(observation,mask)
        expected=original.act(observation,mask)
        assert actual['probabilities']==expected['probabilities']
        assert actual['actionId']==expected['actionId'] and mask[actual['actionId']]
        actions.add(actual['action'])
        observation,_,_,_=env.step(actual['actionId'])
    assert len(actions)>=5


@pytest.mark.parametrize('change',['path','hash','observations'])
def test_controller_rejects_corrupt_or_incompatible_policy_reference(spec,change):
    changed=deepcopy(spec)
    if change=='path': changed['policy']['checkpoint']['path']='../outside.pt'
    elif change=='hash': changed['policy']['checkpoint']['sha256']='0'*64
    else: changed['behavior']['inference']['observationNames']=['bad']
    with pytest.raises(ValueError): FrozenStrategyController(changed,ROOT)


def test_controller_binds_frozen_environment_and_content_identity(spec):
    changed=deepcopy(spec)
    changed['competition']['environmentId']='an_unrelated_competition'
    changed['id']=strategy_identity(changed)
    with pytest.raises(ValueError,match='environment'): FrozenStrategyController(changed,ROOT)
    changed=deepcopy(spec); changed['capabilityRequirements']['targets']['reachM']=.6
    with pytest.raises(ValueError,match='content identity'): FrozenStrategyController(changed,ROOT)


def test_strategy_export_checks_rollout_archive_seal(spec,tmp_path):
    import shutil
    shutil.copyfile(BRIDGE/'analysis.json',tmp_path/'analysis.json')
    (tmp_path/'episodes.jsonl.gz').write_bytes(b'changed rollout source')
    with pytest.raises(ValueError,match='provenance mismatch'): make_spec(ROOT,tmp_path)


def test_saved_profiles_distinguish_seed_blocks_from_unique_capabilities():
    report=json.loads((BRIDGE/'analysis.json').read_text())
    for stage in ('calibration','confirmation'):
        for name in ('balanced','drive_priority','handling_priority','reach_priority'):
            row=report['summaries'][stage]['profile_'+name]
            assert row['capabilityConfigurations']==1
            assert row['capabilitySeedBlocks']==16
            assert row['intervalSamplingUnit']=='episode_seed_blocks_at_one_fixed_capability'


def test_capability_feedback_changes_actual_policy_rollouts_and_recommendations(spec):
    low=feedback_record(spec); low['capabilities']['reachM']=.32
    sufficient=deepcopy(low); sufficient['capabilities']['reachM']=.455
    a=evaluate_feedback(spec,low,ROOT,seeds=[820,821,822,823])
    b=evaluate_feedback(spec,sufficient,ROOT,seeds=[820,821,822,823])
    assert b['meanModeledScore'] > a['meanModeledScore']
    assert b['actionFrequencies'] != a['actionFrequencies']
    assert any(r.get('capability')=='reachM' for r in a['recommendations'])
    assert not any(r.get('capability')=='reachM' for r in b['recommendations'])
    assert a['capabilitySource']=='predicted' and not a['physicalPerformanceValidated']
    assert 'not supplied predictions or measurements' in a['inheritedModelAssumptions']['basis']
    assert not b['automaticCoOptimizationImplemented'] and b['optimizerUpdates']==0


@pytest.mark.parametrize('change',['identity','probability','provenance','uncertainty','boolean','units','unsupported'])
def test_feedback_rejects_unqualified_records_without_projecting_them(spec,change):
    data=feedback_record(spec)
    if change=='identity': data['strategySpecId']='wrong'
    elif change=='probability': data['capabilities']['acquisitionSuccessProbability']=1.1
    elif change=='provenance': data['source']='verified_by_ai'
    elif change=='uncertainty': data['uncertainty']['reachM']=-.1
    elif change=='boolean': data['capabilities']['driveSpeedMps']=True
    elif change=='units': data['units']='inches'
    else: data['capabilities']['torqueNm']=2.
    with pytest.raises(ValueError): evaluate_feedback(spec,data,ROOT,seeds=[1,2,3,4])
