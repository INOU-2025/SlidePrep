"""ResultWriter that fans a single write out to multiple writers."""

from typing import Any, List

from .result_writer import ResultWriter


class MultiResultWriter(ResultWriter):
    """Delegates a write to several ResultWriter instances.

    Each sub-writer receives the same path and independently normalizes
    its own extension, so writers producing different formats (e.g. JSON
    and CSV) don't collide on the same file.
    """

    def __init__(self, writers: List[ResultWriter]) -> None:
        self._writers = writers

    def write(self, path: str, results: Any, metadata: Any = None) -> None:
        errors = []
        for writer in self._writers:
            try:
                writer.write(path, results, metadata)
            except Exception as e:
                errors.append(f"{type(writer).__name__}: {e}")

        if errors:
            raise RuntimeError(
                f"{len(errors)} of {len(self._writers)} writers failed: "
                + "; ".join(errors)
            )
