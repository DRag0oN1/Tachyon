"""Owner-workspace strategy endpoints; main app supplies session middleware."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from . import strategy_runtime as runtime

router = APIRouter(prefix="/api/strategy")


class _DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class GenerateRequest(_DTO):
    competition_id: str = Field(min_length=1, max_length=120)


class StrategyStatus(_DTO):
    available: bool
    competitionId: Literal["v5-override-v2.1"]
    environmentId: Literal["override_abstract_strategy_v2_cups"]
    reason: str | None = None
    policyParameterHash: str | None = None


class Competition(_DTO):
    id: Literal["v5-override-v2.1"]
    environmentId: Literal["override_abstract_strategy_v2_cups"]
    name: Literal["V5 Override"]
    version: Literal["2.1"]


class Rollout(_DTO):
    events: list[dict[str, Any]] = Field(min_length=1, max_length=256)
    score: float = Field(ge=0)
    pointsByObjective: dict[str, int]
    capabilities: dict[str, Any]
    actionFrequencies: dict[str, float]
    policyParameterHash: Literal["b9d0ff5931f9a5c35b2fb407d5051ee08a698a83ad7cfc8537d1967bd60eb5f1"]
    simulationOnly: Literal[True]
    decisions: list[dict[str, Any]] = Field(min_length=1, max_length=256)
    summary: dict[str, Any]
    evidence: dict[str, Any]

    @model_validator(mode="after")
    def validate_episode(self):
        evidence, summary = self.evidence, self.summary
        names = evidence.get("actionNames", [])
        observation_names = evidence.get("observationNames", [])
        if (len(names) != 16 or len(observation_names) != 57 or len(set(names)) != 16
                or len(self.events) != len(self.decisions)
                or summary.get("done") is not True or summary.get("elapsed") != 105.0
                or summary.get("steps") != len(self.events)
                or summary.get("score") != self.score
                or summary.get("capabilities") != self.capabilities
                or summary.get("points_by_objective") != self.pointsByObjective
                or sum(self.pointsByObjective.values()) != self.score
                or self.events[-1].get("score_after") != self.score
                or evidence.get("freshNeuralInference") is not True
                or evidence.get("runtime") != "FrozenStrategyController"
                or evidence.get("trainingPerformed") is not False
                or evidence.get("parameterHashAfter") != self.policyParameterHash
                or evidence.get("environmentId") != runtime.ENVIRONMENT_ID
                or set(self.actionFrequencies) != set(names)):
            raise ValueError("Invalid complete frozen episode")
        for index, (event, decision) in enumerate(zip(self.events, self.decisions)):
            action = decision.get("actionId")
            probabilities = decision.get("probabilities", [])
            mask = decision.get("actionMask", [])
            observation = decision.get("observation", [])
            if (type(action) is not int or not 0 <= action < len(names)
                    or len(mask) != len(names) or any(type(legal) is not bool for legal in mask)
                    or not mask[action] or len(probabilities) != len(names)
                    or len(observation) != len(observation_names)
                    or any(type(value) not in (int, float) or not -1e-6 <= value <= 1 + 1e-6
                           for value in observation)
                    or any(type(value) not in (int, float) or not 0 <= value <= 1 for value in probabilities)
                    or abs(sum(probabilities) - 1) > 1e-5
                    or any(probabilities[i] != 0 for i, legal in enumerate(mask) if not legal)
                    or action != max(range(len(names)), key=lambda i: probabilities[i])
                    or event.get("action_id") != action or event.get("action") != names[action]
                    or decision.get("policyParameterHash") != self.policyParameterHash
                    or decision.get("strategySpecId") != runtime.SPEC_ID
                    or decision.get("step") != index):
                raise ValueError("Invalid neural decision trace")
        for name, frequency in self.actionFrequencies.items():
            if abs(frequency - sum(event["action"] == name for event in self.events) / len(self.events)) > 1e-10:
                raise ValueError("Invalid observed action frequency")
        return self


class GeneratedStrategy(_DTO):
    id: Literal["strategy-spec-4c5452f1550499ebcd54cab6"]
    competition: Competition
    strategyFamily: Literal["low_quadrant_cycles"]
    source: Literal["trained_ppo"]
    performanceDomain: Literal["abstract_simulation_only"]
    spec: dict[str, Any]
    architectures: list[dict[str, Any]] = Field(min_length=2, max_length=2)
    rollout: Rollout
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_saved_references(self):
        spec, rollout = self.spec, self.rollout
        inference = spec["behavior"]["inference"]
        evidence = rollout.evidence
        if (rollout.capabilities != spec["capabilityRequirements"]["referenceCapabilities"]
                or evidence.get("checkpoint") != spec["policy"]["checkpoint"]
                or evidence.get("actionNames") != inference["actionNames"]
                or evidence.get("observationNames") != inference["observationNames"]
                or evidence.get("strategySpecId") != self.id
                or evidence.get("competitionId") != self.competition.id):
            raise ValueError("Inference evidence disagrees with the saved strategy")
        return self


def _error(error):
    return JSONResponse(error.public(), status_code=error.status,
                        headers={"Cache-Control": "private, no-store"})


@router.get("/status", response_model=StrategyStatus, response_model_exclude_none=True)
def strategy_status(request: Request):
    return runtime.status(request.app.state.settings.root)


@router.post("/generate", response_model=GeneratedStrategy)
def generate_strategy(body: GenerateRequest, request: Request):
    try:
        result = runtime.generate(request.app.state.settings.root, body.competition_id)
        return GeneratedStrategy.model_validate(result)
    except runtime.StrategyRuntimeError as error:
        return _error(error)
    except (ValidationError, ValueError, TypeError, KeyError, IndexError, OverflowError):
        return _error(runtime.StrategyRuntimeError("RL_RUNTIME_OUTPUT_INVALID"))
