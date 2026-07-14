"""Sets up the dependency injection container with all required services.

Call bootstrap() once at application startup to initialize services.
"""

from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

from simple_lama_inpainting import SimpleLama

from src.core.container import Container, build_container
from src.core.logger import Logger
from src.core.debugger import Debugger
from src.core.app_config_manager import AppConfigManager
from src.utils import get_extension_for_format
from src.utils.debug.drawer import Drawer
from src.utils.debug.result_writer import ResultWriter
from src.core.context import PipelineContext

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from api import AppConfig


def _check_format_pattern_match(config_manager: AppConfigManager) -> None:
    """Reject configs where img_conversion.format can't satisfy stitching.pattern.

    StitchingStep globs tiles using stitching.pattern verbatim (placeholders
    replaced by "*"). If the configured output format writes a different
    extension, that glob is guaranteed to match zero tiles — this isn't a
    degraded-but-usable state, it's an invalid config, so it must fail here
    at startup rather than twenty minutes into a run when stitching silently
    finds nothing.
    """
    img_conversion = config_manager.img_conversion_config
    stitching = config_manager.stitching_config
    if img_conversion is None or stitching is None:
        return

    expected_ext = get_extension_for_format(img_conversion.format).lower()
    pattern_ext = os.path.splitext(stitching.pattern)[1].lower()

    # Literal comparison: StitchingStep's glob matches the pattern's extension
    # verbatim, so ".tif" and ".tiff" are NOT interchangeable here even though
    # they're the same format — a pattern ending in ".tiff" will never match
    # a file actually written with ".tif" (or vice versa).
    if pattern_ext != expected_ext:
        raise ValueError(
            f"img_conversion.format={img_conversion.format!r} produces "
            f"{expected_ext!r} files, but stitching.pattern={stitching.pattern!r} "
            f"expects {pattern_ext!r} files — StitchingStep's glob would find zero "
            f"tiles. Align img_conversion.format and stitching.pattern's extension."
        )


def bootstrap(
    config_path: str | None = None,
    drawer: Optional[Drawer] = None,
    writer: Optional[ResultWriter] = None,
    *,
    config: AppConfigManager | "AppConfig" | None = None,
    image_shape: tuple[int, int] | None = None,
) -> Container:
    """Build and initialize a new :class:`Container` instance."""

    if config is not None:
        config_manager = (
            config
            if isinstance(config, AppConfigManager)
            else AppConfigManager.from_app_config(config)
        )
    else:
        if config_path is None:
            raise ValueError("Either config_path or config must be provided")
        config_manager = AppConfigManager(config_path)

    _check_format_pattern_match(config_manager)

    logger = Logger(config_manager.log_config, enabled=config_manager.logger_active)

    debugger = Debugger(
        logger,
        config_manager.debug_config,
        config_manager.debug_active,
        drawer=drawer,
        writer=writer,
    )

    context = PipelineContext(image_shape=image_shape)

    container = build_container(logger=logger, debugger=debugger, context=context)
    container.register_singleton("config", config_manager)
    container.register_lazy_singleton("simple_lama", SimpleLama)

    return container
