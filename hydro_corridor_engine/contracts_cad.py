"""Chat 0 Master Contract (Part 1): CAD Layers, Text Styles, Color Ramps & Title Blocks."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

ANCHOR_GUIDE_LAYER = "SV-TEMPLATE-ANCHORS"
STANDARD_LINETYPES = ("CONTINUOUS", "DASHED", "HIDDEN", "CENTER", "PHANTOM")
DYNAMIC_TOKENS = (
    "{{PROJECT_TITLE}}", "{{DRAWING_TYPE}}", "{{SURVEY_DATE}}", "{{T0_T1_EPOCHS}}",
    "{{DATUM_INFO}}", "{{SCALE_TEXT}}", "{{KP_RANGE}}", "{{SHEET_INDEX}}", "{{SURVEYOR}}",
)

@dataclass(frozen=True)
class CadLayerSpec:
    name: str
    aci: int
    linetype: str
    weight_mm: float
    plot: bool = True

@dataclass(frozen=True)
class CadTextStyleSpec:
    name: str
    font: str
    width_factor: float
    paper_height_mm: float

    def model_height(self, plot_scale: float) -> float:
        return (self.paper_height_mm * plot_scale) / 1000.0

@dataclass(frozen=True)
class ColorBand:
    z_low: float
    z_high: float
    rgba: tuple[int, int, int, int]
    aci_safe: int
    label: str

@dataclass(frozen=True)
class ColorTableSpec:
    ramp_id: str
    ramp_mode: Literal["BATHY", "DREDGING", "S2S_DIFF"]
    datum_convention: Literal["ELEVATION_NEG_DOWN", "DEPTH_POS_DOWN"] = "ELEVATION_NEG_DOWN"
    interpolation: Literal["DISCRETE", "LINEAR"] = "DISCRETE"
    deadband_m: float = 0.0
    invert_polarity_palette: bool = False
    paper_safe_aci: bool = True
    bands: tuple[ColorBand, ...] = ()
    underflow_band: ColorBand | None = None
    overflow_band: ColorBand | None = None

@dataclass(frozen=True)
class AnchorBox:
    name: str
    bbox_mm: tuple[float, float, float, float]
    grow_mode: Literal["FIT_CENTER", "TOP_DOWN", "BOTTOM_UP"] = "FIT_CENTER"

@dataclass(frozen=True)
class TitleBlockManifest:
    template_id: str
    cached_dxf_path: str
    layout_name: str = "Layout1"
    paper_size_mm: tuple[float, float] = (841.0, 594.0)
    titleblock_block_name: str = ""
    binding_mode: Literal["ATTRIB", "TOKEN", "HYBRID_ATTRIB_AND_TOKEN"] = "HYBRID_ATTRIB_AND_TOKEN"
    tag_map: dict[str, str] = field(default_factory=dict)
    anchors_mm: dict[str, AnchorBox] = field(default_factory=dict)

_RAW_LAYERS: tuple[tuple[str, int, str, float, bool], ...] = (
    ("SV-BATHY-CONT-MAJ", 4, "CONTINUOUS", 0.30, True),
    ("SV-BATHY-CONT-MIN", 8, "CONTINUOUS", 0.13, True),
    ("SV-BATHY-CONT-TXT", 7, "CONTINUOUS", 0.18, True),
    ("SV-BATHY-SNDG", 7, "CONTINUOUS", 0.18, True),
    ("SV-BATHY-SNDG-SHOAL", 1, "CONTINUOUS", 0.25, True),
    ("SV-ISOP-CUT-CONT", 5, "CONTINUOUS", 0.25, True),
    ("SV-ISOP-FILL-CONT", 30, "DASHED", 0.25, True),
    ("SV-ISOP-SPOT-DZ", 7, "CONTINUOUS", 0.18, True),
    ("SV-ISOP-LIMIT", 6, "PHANTOM", 0.35, True),
    ("SV-ZONE-POLY", 6, "DASHED", 0.35, True),
    ("SV-DSGN-PLAN", 1, "CONTINUOUS", 0.35, True),
    ("SV-RPL-CL", 1, "CENTER", 0.35, True),
    ("SV-RPL-KP-TICK", 7, "CONTINUOUS", 0.25, True),
    ("SV-XLINE-PLAN", 9, "CONTINUOUS", 0.15, True),
    ("SV-PROF-T0-BASE", 8, "DASHED", 0.20, True),
    ("SV-PROF-T1-SURV", 5, "CONTINUOUS", 0.35, True),
    ("SV-PROF-DSGN", 1, "CONTINUOUS", 0.35, True),
    ("SV-PROF-PAY-TOL", 3, "HIDDEN", 0.25, True),
    ("SV-PROF-GRID", 252, "CONTINUOUS", 0.09, True),
    ("SV-PROF-BAND", 7, "CONTINUOUS", 0.20, True),
    ("SV-SECT-HATCH-CUT", 30, "CONTINUOUS", 0.13, True),
    ("SV-SECT-HATCH-OVD", 140, "CONTINUOUS", 0.13, True),
    ("SV-ANNO-TABLE", 7, "CONTINUOUS", 0.25, True),
    ("SV-ANNO-TBLK", 7, "CONTINUOUS", 0.35, True),
    ("SV-ANNO-VPORT", 254, "CONTINUOUS", 0.05, False),
)
CAD_LAYERS: dict[str, CadLayerSpec] = {r[0]: CadLayerSpec(*r) for r in _RAW_LAYERS}

CAD_TEXT_STYLES: dict[str, CadTextStyleSpec] = {
    s[0]: CadTextStyleSpec(*s) for s in (
        ("SV_SNDG", "simplex.shx", 0.85, 1.8),
        ("SV_CONT", "simplex.shx", 0.85, 1.6),
        ("SV_BAND", "arial.ttf", 0.90, 2.0),
        ("SV_LABEL", "arial.ttf", 1.00, 2.5),
        ("SV_TITLE", "arial.ttf", 1.00, 3.5),
    )
}
