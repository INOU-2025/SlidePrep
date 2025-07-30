import cv2
import numpy as np
import os
from typing import Dict

from core.step import PipelineStep
from core.context import PipelineContext
from config.config_schema import GridDetectionConfig
from utils.detection.line_template_factory import LineTemplateFactory
from utils.detection.grid_detection_drawer import GridDetectionDrawer
from utils.detection.analysis import draw_and_analyze_contour
from core.logger import Logger
from core.debugger import Debugger
from typing import Optional


class GridDetectionStep(PipelineStep):
    def __init__(self, config: GridDetectionConfig, logger: Optional[Logger] = None, debugger: Optional[Debugger] = None, **kwargs):
        super().__init__(name="GridDetection", logger=logger, debugger=debugger, **kwargs)
        self.config = config
        factory = LineTemplateFactory(length=config.line_length, thickness=config.line_thickness, angle_deg=config.angle_deg)
        self.templates = {
            "horizontal": factory.create("horizontal"),
            "vertical": factory.create("vertical")
        }

    def run(self, ctx: PipelineContext) -> None:
        if ctx.gray_image is None:
            raise ValueError("gray_image is required for grid detection")

        gray = ctx.gray_image
        fname = ctx.image_name or "unnamed"
        drawer = self.debugger.create_drawer(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)) if self.debugger else None

        inverted = cv2.bitwise_not(gray)
        thresholds = {
            "horizontal": self.config.horizontal_area_threshold,
            "vertical": self.config.vertical_area_threshold,
            "length": 0.55 * max(gray.shape)
        }

        stats = {"accept": 0, "reject": 0, "maybe": 0}
        for key, tmpl in self.templates.items():
            t_h, t_w = tmpl.shape
            pad = (t_h // 2, t_w // 2)
            padded = cv2.copyMakeBorder(inverted, *pad, *pad[::-1], cv2.BORDER_CONSTANT, value=0)
            result = cv2.matchTemplate(padded, tmpl, cv2.TM_SQDIFF_NORMED)
            mask = (result < np.percentile(result, self.config.percentile_thresh)).astype(np.uint8) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                if cv2.contourArea(cnt) >= thresholds[key]:
                    a, r, m = draw_and_analyze_contour(
                        cnt, gray, key, np.array([t_w // 2, t_h // 2]) - [pad[1], pad[0]],
                        thresholds, drawer, fname, self.config.margin, self.logger
                    )
                    stats["accept"] += a
                    stats["reject"] += r
                    stats["maybe"] += m

        if drawer:
            drawer.save(fname)
        self.log(f"Processed {fname}. Accept: {stats['accept']}, Reject: {stats['reject']}, Maybe: {stats['maybe']}")