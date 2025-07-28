import cv2
import numpy as np

class GridDetectionDrawer:
    def __init__(self, overlay: np.ndarray, enabled: bool = True) -> None:
        self.overlay: np.ndarray = overlay
        self.enabled: bool = enabled

    def draw_box(
        self, 
        box: np.ndarray, 
        color: tuple[int, int, int] = (0, 255, 255), 
        thickness: int = 1
    ) -> None:
        if self.enabled:
            cv2.drawContours(self.overlay, [box], 0, color, thickness)

    def draw_contour(
        self, 
        contour: np.ndarray, 
        accepted: bool = False, 
        maybe: bool = False
    ) -> None:
        if not self.enabled:
            return
        if accepted:
            color: tuple[int, int, int] = (0, 0, 255)      # Red
            thickness: int = 2
        elif maybe:
            color = (0, 255, 0)      # Green
            thickness = 2
        else:
            color = (255, 0, 0)      # Blue
            thickness = 2
        cv2.drawContours(self.overlay, [contour], 0, color, thickness)

    def save(self, out_path: str) -> None:
        if self.enabled:
            cv2.imwrite(out_path, self.overlay)