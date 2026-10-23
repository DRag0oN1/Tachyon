# Third-party notices

## Devpost Learn Skill Pack

- Upstream: <https://github.com/challengepost/learn-ai-basics>
- Local canonical files: `.agents/skills/`
- Source/install metadata: `skills-lock.json`
- Copyright: Copyright (c) 2026 Devpost
- License: MIT, reproduced in [LICENSES/devpost-learn-ai-basics-MIT.txt](LICENSES/devpost-learn-ai-basics-MIT.txt)
- Purpose: the official six-stage planning, learning, build, and shipping workflow.

The six skills and their templates/references are third-party curriculum, not
Tachyon application implementation. Their contents have been retained unchanged.
Duplicate local agent installations are excluded from commits.

## Application dependencies and CAD assets

No third-party application implementation or CAD geometry has been incorporated
or bundled. The pre-build verification script imports `cadquery-ocp==8.0.1.1.0`
in a separate temporary Python 3.12 environment for native BRep inspection;
the [binding package declares Apache-2.0](https://pypi.org/project/cadquery-ocp/8.0.1.1.0/).
Its upstream software and transitive dependency notices remain distinct from
manufacturer asset rights. No package binaries are vendored here. See
[CAD source status](docs/cad-source-status.md) for inspected original hashes,
operation restrictions, and the no-redistribution decision.

Record each selected application library
and CAD source, applicable version or content identity, license, distribution
conditions, and required attribution here or in a linked asset manifest before
incorporation. Public availability alone does not establish reuse permission.
