import cv2

class GridDetectionDrawer:
    def __init__(self, overlay, enabled=True):
        self.overlay = overlay
        self.enabled = enabled

    def draw_box(self, box, color=(0, 255, 255), thickness=1):
        if self.enabled:
            cv2.drawContours(self.overlay, [box], 0, color, thickness)

    def draw_contour(self, contour, accepted=False, maybe=False):
        if not self.enabled:
            return
        if accepted:
            color = (0, 0, 255)      # Red
            thickness = 2
        elif maybe:
            color = (0, 255, 0)      # Green
            thickness = 2
        else:
            color = (255, 0, 0)      # Blue
            thickness = 2
        cv2.drawContours(self.overlay, [contour], 0, color, thickness)

    def save(self, out_path):
        if self.enabled:
            cv2.imwrite(out_path, self.overlay)