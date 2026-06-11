"""ProductConfig registry.

Loads per-product configuration from prompts/products/{product_id}.txt at startup.
Adding a new product requires only a new DB row and a new text file — no code changes.

Each config file is a simple INI-style file with [product], [design_fit],
[scoring_hints], and [mockup] sections.
"""

from __future__ import annotations

import configparser
import json
from dataclasses import dataclass
from pathlib import Path

_PRODUCTS_DIR = Path(__file__).parent.parent / "prompts" / "products"


@dataclass
class ProductConfig:
    product_id: str
    product_name: str
    category: str
    price_paise: int
    print_area_width_in: float
    print_area_height_in: float
    min_complexity: str
    max_complexity: str
    production_time_min: int
    colors: list[str]
    sizes: dict[str, bool]
    units_total: int
    # design_fit scores keyed by VariantStyle value
    design_fit_scores: dict[str, float]
    # scoring hints
    best_for: str
    not_ideal_for: str
    placement_default: str
    placement_alternatives: list[str]
    low_stock_threshold: int
    # mockup
    suggested_colors_by_theme: dict[str, str]
    default_color: str
    placement: str
    size_default: str


def _load_product_config(path: Path) -> ProductConfig:
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")

    p = cfg["product"]
    df = cfg["design_fit"]
    sh = cfg["scoring_hints"]
    mk = cfg["mockup"]

    alts_raw = sh.get("placement_alternatives", "none")
    alternatives = [] if alts_raw.strip() == "none" else [a.strip() for a in alts_raw.split(",")]

    return ProductConfig(
        product_id=p["product_id"],
        product_name=p["product_name"],
        category=p["category"],
        price_paise=int(p["price_paise"]),
        print_area_width_in=float(p["print_area_width_in"]),
        print_area_height_in=float(p["print_area_height_in"]),
        min_complexity=p["min_complexity"],
        max_complexity=p["max_complexity"],
        production_time_min=int(p["production_time_min"]),
        colors=json.loads(p["colors"]),
        sizes=json.loads(p["sizes"]),
        units_total=int(p["units_total"]),
        design_fit_scores={
            "illustration": float(df.get("illustration", 0.8)),
            "geometric": float(df.get("geometric", 0.8)),
            "watercolor": float(df.get("watercolor", 0.8)),
            "minimalist": float(df.get("minimalist", 0.8)),
        },
        best_for=sh.get("best_for", ""),
        not_ideal_for=sh.get("not_ideal_for", ""),
        placement_default=sh.get("placement_default", "center_chest"),
        placement_alternatives=alternatives,
        low_stock_threshold=int(sh.get("low_stock_threshold", "5")),
        suggested_colors_by_theme=json.loads(mk["suggested_colors_by_theme"]),
        default_color=mk["default_color"],
        placement=mk["placement"],
        size_default=mk["size_default"],
    )


def load_product_registry(
    products_dir: Path | None = None,
) -> dict[str, ProductConfig]:
    """Load all *.txt files from the products directory into a registry dict.

    Returns {product_id: ProductConfig}. Safe to call at startup — any
    malformed file raises immediately so misconfiguration is caught early.
    """
    directory = products_dir or _PRODUCTS_DIR
    registry: dict[str, ProductConfig] = {}
    for path in sorted(directory.glob("*.txt")):
        config = _load_product_config(path)
        registry[config.product_id] = config
    return registry


# Module-level singleton loaded once at import time.
# Tests can override by calling load_product_registry(custom_dir).
PRODUCT_REGISTRY: dict[str, ProductConfig] = load_product_registry()
