# LostLink — AI-Powered Campus Lost & Found
A lost and found system with browser which shows lost and found items with details.

Pure Python stdlib. No pip installs. Runs in VS Code.

## Quick start

```bash
python main.py demo        # full AI demo (inference, search, explanations, benchmark)
python main.py serve       # http://127.0.0.1:8000/  → API-driven UI
                           # http://127.0.0.1:8000/offline → original HTML demo
python main.py bench       # baseline vs heuristic
python main.py             explain <lost_id> <found_id>
python main.py reset       # re-seed demo data
python main.py test        # unit tests
