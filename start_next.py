"""Compatibility alias. Every source launcher opens the same main window."""
from start import launch

if __name__ == '__main__':
    raise SystemExit(launch())
