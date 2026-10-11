# Contributing to Switchyard

1. Fork the repository and create your branch from `main`.
2. Ensure you have installed backend (`uv pip install -e ".[dev]"`) and frontend dependencies (`npm install`).
3. Run the CI guard before submitting:
   ```bash
   python scripts/check_no_simulation.py
   pytest
   npm run lint
   ```
4. Adhere strictly to the **No Simulation Policy**: Production endpoints must not contain mock tokens, fake responses, or synthetic fallbacks. Degraded states must yield HTTP 503 RFC 7807 problem payloads.
5. Open a Pull Request with a clear description and test coverage.
