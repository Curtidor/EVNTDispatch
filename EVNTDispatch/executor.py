import logging

from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, List, Union

from EVNTDispatch.c_logger import CLogger


class Executor:
    def __init__(self, max_workers: int = None):
        """
        Initialize the Executor.
        :param max_workers: The maximum number of workers in the pool.
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._logger = CLogger('Executor', logging.INFO, {logging.StreamHandler(): logging.INFO})

    def submit(self, fn: Callable, *args: Any, is_scheduled_task: bool = False, **kwargs: Any,) -> Future:
        """
        Submits a callable function for execution.

        :param fn: The callable function to execute.
        :param args: Arguments to pass to the function.
        :param is_scheduled_task: bool to indicate if the submission comes from the scheduling system, external users should never
               set it to 'True' as it will lead to unexpected behaviour
        :param kwargs: Keyword arguments to pass to the function.
        :return: Future object representing the execution of the function.
        """
        try:
            future = self._executor.submit(fn, *args, **kwargs)

            if is_scheduled_task:
                return future

            return future
        except Exception as e:
            self._logger.error(f"Exception occurred while submitting task: {e}")
            raise

    def map(self, fn: Callable, *iterables: Any, timeout: Union[int, None] = None) -> List[Any]:
        """
        Maps a function across multiple iterables.

        :param fn: The function to map across iterables.
        :param iterables: Iterables to pass to the function.
        :param timeout: Timeout for the operation.
        :return: List of results from the mapped function.
        """
        try:
            return list(self._executor.map(fn, *iterables, timeout=timeout))
        except Exception as e:
            self._logger.error(f"Exception occurred during mapping: {e}")
            raise

    def shutdown(self, wait: bool = True):
        """
        Shuts down the executor.

        :param wait: Flag indicating whether to wait for pending tasks to complete before shutting down.
        """
        try:
            self._executor.shutdown(wait=wait)
        except Exception as e:
            self._logger.error(f"Exception occurred during shutdown: {e}")
            raise
