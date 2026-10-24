"""Actual learned artifact crosses into the Torch-free server design module."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT=Path(__file__).parents[3]
STRATEGY=ROOT/"research/strategy_rl/results/strategy-design-bridge-v1/strategy-spec-v2.json"


def run_designer(spec_path, output):
    script="""
import json,sys
from pathlib import Path
from tachyon.design import emit
spec=json.loads(Path(sys.argv[1]).read_text())
result=emit(spec,sys.argv[2])
assert not any(m.split('.')[0] in ('torch','numpy','tachyon_strategy_rl') for m in sys.modules)
assert 'tachyon.app' not in sys.modules and 'tachyon.cad' not in sys.modules
print(json.dumps(result))
"""
    return subprocess.run([sys.executable,"-c",script,str(spec_path),str(output)],
                          env={**os.environ,"PYTHONPATH":str(ROOT/"server")},capture_output=True,text=True,check=True)


def test_real_neural_strategy_artifact_generates_two_structured_engineering_alternatives(tmp_path):
    run_designer(STRATEGY,tmp_path/"design")
    spec=json.loads(STRATEGY.read_text())
    proposals=json.loads((tmp_path/"design/architecture-proposals.json").read_text())
    requirements=json.loads((tmp_path/"design/design-requirements.json").read_text())
    assert len(proposals)==2
    assert proposals[0]['mechanicalSignature'] != proposals[1]['mechanicalSignature']
    assert all(p['strategyId']==spec['id'] and p['strategyFamily']=='low_quadrant_cycles' for p in proposals)
    assert all(not p['cadGenerated'] and not p['completeRobot'] and p['newStrategyFamiliesClaimed']==0 for p in proposals)
    assert proposals[0]['requirements']==proposals[1]['requirements']==requirements['requirements']
    for p in proposals:
        budget=p['cycleBudgetIntent']
        assert budget['recurringAcquisitions']==budget['recurringPlacements']==2
        assert budget['recurringPinCupActionSeconds']==7.2
        assert budget['remainingTravelFailureAndOtherTimeSeconds'] < 3.


def test_synthetic_changed_mechanical_requirements_change_design_specification(tmp_path):
    # This is a contract perturbation, NOT evidence of another learned family.
    high=deepcopy(json.loads(STRATEGY.read_text()))
    high['id']='synthetic-high-reach-contract'
    high['capabilityRequirements']['hardMinimums']['reachM']=.62
    high['capabilityRequirements']['targets']['reachM']=.62
    high['capabilityRequirements']['targets']['driveSpeedMps']=2.
    high['evidence']['contractPerturbation']='Synthetic requirements only, not discovered by PPO'
    source=tmp_path/'high.json'; source.write_text(json.dumps(high))
    run_designer(source,tmp_path/'high')
    run_designer(STRATEGY,tmp_path/'low')
    a=json.loads((tmp_path/'high/architecture-proposals.json').read_text())
    b=json.loads((tmp_path/'low/architecture-proposals.json').read_text())
    assert a[0]['requirements']!=b[0]['requirements']
    assert a[0]['mechanicalSignature']!=b[0]['mechanicalSignature']
    assert a[0]['subsystems']!=b[0]['subsystems']
