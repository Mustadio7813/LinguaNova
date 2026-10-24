from pathlib import Path
import shutil
import tempfile
import os


class Staging:
    def __init__(self, destination):
        self.destination=Path(destination)
        self.directory=None

    def __enter__(self):
        self.destination.parent.mkdir(parents=True,exist_ok=True)
        self.directory=Path(tempfile.mkdtemp(prefix='stage-',dir=self.destination.parent))
        return self.directory

    def publish(self):
        previous=self.destination.with_name(self.destination.name+'.previous')
        if previous.exists():
            shutil.rmtree(previous)
        if self.destination.exists():
            self.destination.rename(previous)
        try:
            self.directory.rename(self.destination)
            self.directory=None
        except Exception:
            if previous.exists():
                previous.rename(self.destination)
            raise

    def __exit__(self,*args):
        if self.directory and self.directory.exists():
            shutil.rmtree(self.directory)
