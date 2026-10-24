import numpy as np
import pytest

from tachyon_strategy_rl.capability_analysis import DiagnosticCapabilities, capabilities_for, variants, episode
from tachyon_strategy_rl.environment import Capabilities, Env, sample_capabilities
from tachyon_strategy_rl.evaluate import EvaluationCase, rollout
from tachyon_strategy_rl.inference import validated_policy


def test_independent_intervention_updates_actor_observation_and_dynamics_without_rebudgeting():
    base = Capabilities(.25,.5,.25)
    slow = DiagnosticCapabilities(base, {"drive_speed_m_s": .75})
    fast = DiagnosticCapabilities(base, {"drive_speed_m_s": 2.1})
    a, b = Env(seed=22, capabilities=slow), Env(seed=22, capabilities=fast)
    a.step(0); b.step(0)
    assert b.elapsed < a.elapsed
    assert slow.drive == fast.drive == base.drive
    assert slow.vector()[3] == pytest.approx(.75/2.65)
    assert fast.to_dict()["jointDomainStatus"] == "off_training_manifold_diagnostic"
    assert np.isfinite(fast.vector()).all() and np.all(fast.vector() <= 1)


@pytest.mark.parametrize("bad", [{"acceleration": 1.}, {"drive_speed_m_s": True},
                                  {"max_reach_m": float('nan')}, {"placement_seconds": 0.},
                                  {"acquisition_success_probability": 1.1}])
def test_unsupported_or_out_of_domain_interventions_are_rejected(bad):
    with pytest.raises(ValueError): DiagnosticCapabilities(Capabilities(.3,.3,.4),bad)


def test_feasible_controls_preserve_simplex_instead_of_claiming_single_feature_isolation():
    base = Capabilities(.25,.4,.35)
    for variant in variants():
        capability = capabilities_for(base, variant)
        capability.validate()
        assert capability.drive+capability.handling+capability.lift == pytest.approx(1.)


def test_zero_intervention_reproduces_original_frozen_policy_trace_exactly():
    from pathlib import Path
    experiment = Path(__file__).parents[1]/"results/override-ppo-v1"
    model,_=validated_policy(experiment/"runs/seed-17/checkpoint.pt")
    case=EvaluationCase(2000000000,3000000000,"held_out_distribution",2.)
    original=rollout(case,model,include_trace=True)
    diagnostic=episode(model,DiagnosticCapabilities(sample_capabilities(case.capability_seed),{}),case.episode_seed,trace=True)
    assert original['trace'] == diagnostic['trace']
    assert original['score'] == diagnostic['score']
