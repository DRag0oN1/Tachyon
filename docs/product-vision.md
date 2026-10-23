# Tachyon — established product vision

This records the learner's supplied product requirements and final hackathon
scope clarification. It guides the planning documents; it is not itself a scope,
PRD, or technical-specification approval. Application implementation is new work
for this challenge. Third-party libraries, curriculum, and component assets must
retain accurate provenance and applicable licenses.

## Purpose and philosophy

Tachyon is a sophisticated, mobile-first AI robotics design application for VEX
teams. It connects understanding a competition, choosing a strategy, inspecting
a realistic robot, and changing its mechanisms in one coherent workspace.

**Complicatedly Simple:** a beginner can generate and understand a robot while
an experienced roboticist has progressively more control. Avoid redundant panels,
unexplained controls, excessive navigation, and a chatbot-centric layout.
The application should remain useful beyond the hackathon.

## Focused engineering pipeline

Build Tachyon's own small pipeline:

**PDF parsing → structured competition model → LLM strategy and architecture
generation → VEX component selection → assembly construction → 3D rendering.**

Keep a small supported set of mechanisms and modifications functional. Do not
build a massive multi-agent research framework. Advanced physics, optimization,
and external integrations must not displace the working core experience.

## Competition selection and interpretation

- Default to VEX V5 Override with a versioned source available without repeated
  uploads. Verify official rules rather than fabricating them.
- Accept supported VEX rulebook PDFs through a general competition model.
  Extract objectives, scoring opportunities, game elements, relevant field
  locations, autonomous/driver considerations, and robot constraints.
- Keep facts linked to document pages/sections. Show incomplete, ambiguous,
  unsupported, or failed extraction explicitly.
- Demonstrate another supported competition through the same pipeline. Keep
  game-specific scoring semantics separate from the application workflow.

## Independent entry points and distinct alternatives

**Generate Strategy** works without a robot: produce competition-aware
objectives, mechanism requirements, and execution sequences with clear rationale.
A strategy can later become a design.

**Create Robot** works independently of a separate strategy session: start from
competition rules, a desired robot description, priorities, or an available design.
CAD/sketch uploads are future options until actually implemented.

The automated flow generates two meaningfully different candidate architectures
and connected conceptual robot designs. Mechanical differences must be visible
in subsystems, configuration, or power transmission; different colors or labels
are insufficient. Preserve strategy/design associations and comparison/refinement.

## Authentic component geometry and assembly integrity

Authentic VEX CAD is the highest engineering and visual priority. Use actual,
appropriately licensed component geometry, with verified source identity,
scale/units, transforms, dimensions, and metadata. Distinguish manufacturer CAD,
other sourced component CAD, and any explicitly conceptual geometry accurately.
Public availability does not establish a license.

Support a curated set of relevant structural channels/plates, wheels, motors and
mounts, shafts/couplers, gears or other transmissions, bearings, retention parts,
spacers/fasteners, and acquisition/scoring mechanisms. Assemble complete
conceptual robots whose important subsystems are mounted and recognizable.
A drivetrain alone does not satisfy completeness.

Keep a real assembly hierarchy, mounting and transmission relationships, shaft
alignment, joints/limits, and meaningful clearances. Choose drivetrain and
mechanisms from the architecture requirements. Do not default to independently
driven wheels simply because they are easy to place.

Preserve source CAD separately from derived browser meshes. Mesh display is not
editable solid CAD. Do not silently replace missing parts with primitives and
call them authentic, or infer physical buildability from an attractive render.
Missing geometry and unsupported mechanical relationships must be exposed.

## Immersive CAD workspace

The CAD canvas fills the available robot-inspection screen. Contextual floating
controls open dismissible strategy, component, alternative, display/orientation,
animation, edit, and supported export views. Panels collapse, reopen, and resize
where practical without obscuring most of the robot or duplicating information.

Support orbit, zoom, pan, phone gestures, component selection, subsystem
highlighting, isolation/hiding, exploded views, display modes, relevant joint
animation, and hierarchy inspection. Unsupported motion cannot be presented as
validated operation. Keep the active design and selection clear.

## Strategy-to-CAD linkage

Every robot has a prominent Strategy action. Explain its objectives, scoring
opportunities, architecture, operation sequence, field positioning, and tradeoffs
using concise text, annotated mechanical sketches, field playbooks, arrows, and
relevant actual CAD views.

Selecting a strategy action highlights its actual subsystem, focuses the view,
and exposes its explanation and any supported motion. Selecting a mechanism
reveals the actions it supports. Derive all views from shared structured data:

**Competition → Strategy → Objectives → Actions → Mechanisms → Components →
Joints → CAD Geometry → Illustrations.**

Do not generate disconnected strategy text, arbitrary sketches, or unrelated
geometry and claim they form a coherent design.

## Tachyon AI core and functional modifications

A small animated mechanical core stays at the **top-left** of the CAD workspace.
Compact mode includes a text command bubble. Expanded mode becomes a desktop
side panel or touch-friendly mobile sheet; full-screen mode supports complex
review. Expansion/collapse controls belong inside the assistant itself, with
clean return to the core. Do not add a detached three-button mode selector.

Selection supplies component/strategy context. A limited supported request set
must produce actual structured assembly changes and visible CAD updates, with
clear effects and errors. Plan preview, accept/reject, and undo where supported.
Text-only responses cannot count as design modifications. Explain unsupported
requests instead of inventing success. Voice and attachments can follow reliable
implementations later.

## SNAP and SHIFT

| Theme | Established direction |
| --- | --- |
| SNAP | Modern LEGO Technic-inspired modular engineering; warm off-white, graphite, metallic gray, refined yellow/blue/red accents; snapping/docking panels, understandable subsystem separation, compact modular core motion. Sophisticated rather than childish. |
| SHIFT | Refined Transformers-inspired mechanical movement; dark gunmetal/titanium, electric blue and subtle copper/orange; transforming controls, expanding panels, unfolding core shell. Restrained rather than excessively decorative. |

Both preserve functionality, navigation, actual geometry, readable accessible
controls, and engineering data. Theme changes retain workspace state. Motion is
brief and useful, with reduced-motion support. References inspire the interaction
identity; do not copy protected branding or assets.

## Modes, layouts, and mobile use

- **Simple Mode:** guided generation, inspection, understandable strategy,
  basic configuration, and contextual edits.
- **Advanced Mode:** progressively more mechanism/subsystem/architecture detail,
  component inspection, supported adjustments, requirements, and targeted changes.
- **Focus:** full-screen CAD. **Split:** CAD and Strategy. **Studio:** CAD,
  Strategy, and Components. **Custom:** practical panel hiding/resizing and layout
  control. Persist theme/layout/workspace preferences and supported project state.
- Mobile prioritizes focus, large touch targets, pinch zoom, drag orbit, usable
  pan gestures, quick mechanism references, and dismissible sheets/drawers.
  Desktop can show more panes. Do not simply shrink a desktop dashboard.

Unfinished manual editing or import tools must have truthful availability labels
and must not appear as enabled actions that do nothing.

## Verification and acceptance

Verify the real end-to-end workflow: default competition and another supported
PDF; grounded AI strategies; two distinct architectures; complete conceptual
assemblies using real licensed components; correct scale and connections; action
highlighting with sketches/playbooks; and a supported AI edit that changes both
data and rendered geometry. Identify approximations and unknowns explicitly.

Exercise both themes, mobile/desktop, all three AI states, Simple/Advanced modes,
and collapsible/customizable layouts. Run real builds and runtime checks,
including browser interactions/screenshots where available. Verify loading,
missing services, invalid PDFs/CAD, unavailable assets, and generation failures.
Do not fabricate simulation results, scoring success, or physical validation.

## Planning, build, and shipping

Use the official Devpost sequence: `1-start` → `2-scope` → `3-prd` → `4-spec` →
`5-build` → `6-ship`. Preserve scope/PRD/spec drafts and approvals, the build
checklist, and learning wrap-up/app map. Keep established product decisions and
ask only about consequential unresolved choices.

Fast mode is selected. Keep verified runnable increments, meaningful commits,
required early/final reviews, and honest documentation of when work occurred.
Protect credentials; no client-side API keys or secrets in history. Provide
reproducible setup/run instructions as implementation becomes available.

The public repository and demonstration must describe newly implemented Tachyon
functionality and accurately attribute incorporated third-party materials.
The learner authors submission descriptions and reflections. Do not silently
publish, deploy, change visibility, or submit an entry.

## Priorities and future extensions

Prioritize real component geometry, complete assemblies, competition-aware
generation, strategy/CAD coherence, the full-screen mobile workspace, functional
contextual AI, both visual themes, and practical customization. Broader catalogs,
manual CAD/sketch imports, Fusion/external CAD connections, and simulation can
follow through clear extension points with truthful status until verified.
