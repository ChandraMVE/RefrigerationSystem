# RefrigerationSystem

Initial Python skeleton for a 10ft x 10ft x 10ft walk-in refrigeration controller.

## Quick run
```bash
python3 main.py
```

This launches a PyQt GUI with tabs for:
- Monitor UART
- IO UART

Use `python3 main.py --demo` to run the previous console demonstration.

## Repository layout
- `documents/`: design and protocol notes
- `src/refrigeration/`: controller skeleton and UART abstraction
