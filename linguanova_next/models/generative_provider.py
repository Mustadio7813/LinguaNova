from typing import Protocol


class GenerativeProvider(Protocol):
    def restore(self, image, mask, model_directory, parameters, progress=None, cancelled=None):
        """Return background only. Destination and translation are not inputs."""
        ...
