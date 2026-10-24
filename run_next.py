#!/usr/bin/env python3
"""Compatibility entry: the main GUI, or the existing developer CLI commands."""
if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    import sys
    if not sys.argv[1:] or sys.argv[1] in ('classic', 'gui'):
        if sys.argv[1:]:sys.argv.pop(1)
        from run import main
    else:
        from linguanova_next.cli import main
    raise SystemExit(main())
