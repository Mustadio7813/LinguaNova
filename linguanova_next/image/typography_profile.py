from dataclasses import dataclass
from ..util import digest


@dataclass(frozen=True)
class TypographyProfile:
    font_path: str
    font_hash: str
    family: str
    size: int
    color: tuple = (255,255,255,255)
    variant: str = 'Regular'
    weight: int = 400
    italic: bool = False
    stroke_width: int = 0
    stroke_color: tuple = (0,0,0,255)
    shadow_offset: tuple = (0,0)
    shadow_color: tuple = (0,0,0,0)
    line_spacing: int = 4
    tracking: float = 0.0
    alignment: str = 'center'
    rotation: float = 0.0
    baseline: str = 'measured_bbox'
    min_size_ratio: float = 0.85
    max_lines: int = 4
    evidence: str = 'unverified'
    confidence: float = 0.0
    provenance: str = 'manual'
    reviewer: str = ''
    approximation_approved: bool = False
    gradient: str = ''
    texture: str = ''
    schema_version: int = 1

    @property
    def identity(self):
        return digest(self)

    def validate(self):
        if self.schema_version!=1 or self.size<6 or not 0.5<=self.min_size_ratio<=1:
            raise ValueError('Invalid bounded typography profile')
        if self.alignment not in ('left','center','right') or self.max_lines<1:
            raise ValueError('Unsupported text distribution')
        if self.gradient or self.texture:
            raise ValueError('Gradient/textured lettering requires a separate controlled recreation; pending fidelity')
        if self.evidence not in ('identified','approved_approximation','automatic_estimate'):
            raise ValueError('Font identity has not been reviewed')
        if self.evidence=='automatic_estimate' and (not self.provenance or not 0<=self.confidence<=1):
            raise ValueError('Automatic typography requires recorded estimation evidence')
        if self.evidence=='approved_approximation' and not (self.approximation_approved and self.reviewer):
            raise ValueError('Approximate typography requires a named approval')
