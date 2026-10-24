"""Standalone source/frozen inference entry point; never launches the GUI."""
import argparse
import multiprocessing


def main():
    multiprocessing.freeze_support()
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',required=True)
    args=parser.parse_args()
    from .image.generative_worker import worker_main
    return worker_main(args.worker)


if __name__=='__main__':
    raise SystemExit(main())
