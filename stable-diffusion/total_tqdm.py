import math
from loguru import logger
from modules import shared


class TotalTQDM:
    def __init__(self):
        self.reset_state()

    def reset_state(self):
        self.current = 0
        self.total = 0
        self.last_logged_percent = -1
        self.completed = False

    def _should_log(self):
        return True

    def _log_progress(self, force=False):
        if self.total <= 0:
            return

        current_percent = math.floor(100 * self.current / self.total)

        # Логируем только при изменении процента или принудительно
        if force or current_percent != self.last_logged_percent:
            message = f"Total progress: {self.current}/{self.total} ({current_percent}%)"

            if self._should_log():
                logger.info(message)
            else:
                logger.debug(message)

            self.last_logged_percent = current_percent

    def reset(self):
        self.reset_state()
        self.total = shared.state.job_count * shared.state.sampling_steps
        self._log_progress(force=True)

    def update(self):
        if not self._should_log() and not self.completed:
            return

        self.current += 1
        self._log_progress()

        if self.current >= self.total:
            self.completed = True

    def updateTotal(self, new_total):
        self.total = new_total
        self._log_progress(force=True)

    def clear(self):
        if not self.completed and self.current > 0:
            self._log_progress(force=True)
            logger.debug("Operation interrupted")
        self.reset_state()