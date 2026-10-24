"""OS-held process locks; crashes release them, independent of user data path."""
from pathlib import Path
import tempfile
import os
from ..util import digest


class JobLock:
    def __init__(self, project):
        folder=Path(tempfile.gettempdir())/'linguanova-next-locks'
        folder.mkdir(exist_ok=True)
        self.path=folder/(digest(str(Path(project).resolve()).casefold() if os.name=='nt' else str(Path(project).resolve()))+'.lock')
        self.stream=None

    def __enter__(self):
        self.stream=self.path.open('a+b')
        self.stream.seek(0)
        if self.path.stat().st_size==0:
            self.stream.write(b'0');self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.stream.close();self.stream=None
            raise RuntimeError('Another new-flow job is using this project') from None
        return self

    def __exit__(self,*args):
        if self.stream:
            if os.name=='nt':
                import msvcrt
                self.stream.seek(0);msvcrt.locking(self.stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_UN)
            self.stream.close();self.stream=None
