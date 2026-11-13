# GAIA — Heart of the World

An original, modular AI coordination project inspired by the idea of a central intelligence coordinating specialized systems.

> This is an independent project. It uses original names, code, interface elements, and symbols; it does not include ripped game assets.

## Vision

GAIA is the central coordinator. Specialized subsystems handle focused tasks, while GAIA routes requests, tracks subsystem status, and controls activation.

HEPHAESTUS is the subsystem workshop: it can propose new **configuration-only** subsystem blueprints. GAIA must validate a blueprint before it can be registered. Generated blueprints are data, not executable code.

## First milestone

- [x] Establish the project structure
- [x] Add a simple terminal prototype
- [x] Define the initial subsystem registry
- [ ] Add persistent memory
- [ ] Add a subsystem creation/approval workflow
- [ ] Build the visual command interface
- [ ] Add an optional AI provider (with API keys kept outside the repository)

## Run

Requires Python 3.10+.

```bash
python main.py
```

No API key or external service is required for the first prototype.

## Safety and design principles

- Subsystems have limited, explicit roles.
- New subsystem blueprints are reviewed before activation.
- No generated Python or shell code is executed.
- API keys and private credentials must never be committed.
- The interface will use original visual motifs rather than copied Horizon artwork.

## Project layout

```
gaia/
  core.py
data/
  subsystems.json
main.py
requirements.txt
```
