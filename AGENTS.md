# Feed Converter Desktop — Agent Instructions

## Project goal

Build a reliable local desktop tool for semi-automatic XML feed to Excel workflow for real estate projects.

## Development rules

- Reliability and predictability are more important than speed or fewer clicks.
- Do not duplicate business logic in GUI.
- GUI must call existing core modules and services.
- Preserve user-edited Excel fields unless an update profile explicitly allows updating them.
- Do not hardcode absolute paths.
- Use the portable workspace from core.paths.
- Support macOS, Windows and Linux.
- Use pathlib.Path for paths.
- Do not bypass Safety checks.
- Data Engine stores events, not full daily snapshots.
- Keep GUI thin and modular.
- Prefer readable code over clever code.
- Do not add placeholder buttons. If a button exists, it must work.
- Do not add mass update for all projects unless explicitly requested later.
