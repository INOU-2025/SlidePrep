from typing import Any, List, Optional
from src.core.step import PipelineStep
from src.core.container import Container


class Pipeline:
    """
    Sequential pipeline for executing processing steps on data.
    
    This pipeline executes a series of PipelineStep instances in order,
    passing the output of each step as input to the next. It provides
    centralized error handling and logging for the entire processing chain.
    
    The pipeline stops execution if any step raises an exception and returns
    None to indicate failure. All steps are expected to follow the PipelineStep
    interface contract.
    """

    def __init__(self, steps: List[PipelineStep], container: Container) -> None:
        """Initialize pipeline with a sequence of processing steps."""

        self.steps = list(steps)
        self.container = container
        for step in self.steps:
            step.container = container
        try:
            self.logger = container.resolve("logger")
        except KeyError:
            self.logger = None

    def run(self, data: Any) -> Optional[Any]:
        """
        Execute the pipeline on input data.

        Runs each step sequentially, passing the output of each step as input
        to the next. Provides comprehensive error handling and logging for
        the entire processing chain.

        Args:
            data: Initial input data to process. The type depends on what
                 the first step expects to receive.

        Returns:
            The final processed data from the last step, or None if any
            step raises an exception during processing.
        """
        current_data = data
        for step in self.steps:
            try:
                result = step.run(current_data)
                current_data = result[0] if isinstance(result, tuple) else result
                if self.logger:
                    self.logger.debug(
                        f"Step {step.name} completed successfully")
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Pipeline failed at step {step.name}: {e}")
                    self.logger.exception("Full exception details:")
                else:
                    print(f"Error in step {step.name}: {e}")
                return None
        return current_data
