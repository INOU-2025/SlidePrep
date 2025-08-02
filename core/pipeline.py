from typing import Any, List
from core.step import PipelineStep
from core.container import Container


class Pipeline:
    """Simple pipeline that executes steps sequentially."""

    def __init__(self, steps: List[PipelineStep]):
        self.steps = list(steps)
        try:
            self.logger = Container.resolve("logger")
        except KeyError:
            self.logger = None

    def run(self, data: Any) -> Any:
        """Run the pipeline for the provided data.

        Each step receives the output from the previous step. If any step
        raises an exception, the error is logged and processing stops.
        """
        current_data = data
        for step in self.steps:
            try:
                current_data = step.run(current_data)
                if self.logger:
                    self.logger.info(f"Step {step.name} completed")
            except Exception as e:
                if self.logger:
                    self.logger.exception(f"Error in step {step.name}: {e}")
                else:
                    print(f"Error in step {step.name}: {e}")
                return None
        return current_data
