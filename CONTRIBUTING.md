# Contributing

Thanks for helping improve Neon City Chess.

## Development setup

### Desktop (Python)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Browser (TypeScript)

```bash
cd web-chess
npm install
npm run dev
```

## Contribution guidelines

- Keep gameplay deterministic and two-player local first.
- Preserve camera behavior: game-directed by side-to-move, not user-controlled.
- Prefer small focused pull requests.
- Include before/after notes for visual changes.
- Update docs when behavior changes.

## Pull request checklist

- [ ] I tested the change locally.
- [ ] I kept controls and move legality intact.
- [ ] I updated docs and comments where needed.
- [ ] I did not commit build artifacts or secrets.
