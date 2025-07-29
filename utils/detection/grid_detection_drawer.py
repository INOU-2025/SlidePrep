import cv2
import numpy as np

class GridDetectionDrawer:
    """
    Handles drawing and saving overlays for grid/line detection visualization.

    Attributes
    ----------
    overlay : np.ndarray
        The image overlay to draw on.
    enabled : bool
        Whether visualization is enabled.

    Methods
    -------
    draw_box(box, color=(0,255,255), thickness=1)
        Draws a box on the overlay.
    draw_contour(contour, accepted=False, maybe=False)
        Draws a contour with color depending on acceptance/maybe status.
    save(out_path)
        Saves the overlay image to the specified path.
    """

    def __init__(self, overlay: np.ndarray, enabled: bool = True) -> None:
        """
        Initialize the drawer.

        Parameters
        ----------
        overlay : np.ndarray
            The image overlay to draw on.
        enabled : bool, optional
            Whether visualization is enabled (default: True).
        """
        self.overlay: np.ndarray = overlay
        self.enabled: bool = enabled

    def draw_box(
        self, 
        box: np.ndarray, 
        color: tuple[int, int, int] = (0, 255, 255), 
        thickness: int = 1
    ) -> None:
        """
        Draw a box on the overlay.

        Parameters
        ----------
        box : np.ndarray
            The box points.
        color : tuple[int, int, int], optional
            Color for the box (default: yellow).
        thickness : int, optional
            Line thickness (default: 1).
        """
        if self.enabled:
            cv2.drawContours(self.overlay, [box], 0, color, thickness)

    def draw_contour(
        self, 
        contour: np.ndarray, 
        accepted: bool = False, 
        maybe: bool = False
    ) -> None:
        """
        Draw a contour on the overlay.

        Parameters
        ----------
        contour : np.ndarray
            The contour points.
        accepted : bool, optional
            If True, draw in red.
        maybe : bool, optional
            If True, draw in green.
            Otherwise, draw in blue.
        """
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
        """
        Save the overlay image to the specified path.

        Parameters
        ----------
        out_path : str
            Path to save the image.
        """
        if self.enabled:
            cv2.imwrite(out_path, self.overlay)
            # TODO. Fix me
            # log.info(f"Saved output: {out_path}")