import time
from loguru import logger
from typing import Optional, Iterable, Union, Dict, Any


class SilentTqdm:
    def __init__(
            self,
            iterable: Optional[Iterable] = None,
            total: Optional[int] = None,
            desc: Optional[str] = None,
            mininterval: float = 0.1,
            logger_level: str = "INFO",
            logging_interval: Union[int, float] = 1,
            **kwargs
    ):
        """
        Параметры:
        iterable: Итерируемый объект
        total: Общее количество элементов
        desc: Описание прогресса
        mininterval: Минимальный интервал между логированиями (в секундах)
        logger_level: Уровень логирования (INFO, DEBUG и т.д.)
        logging_interval: Интервал логирования в шагах или процентах
        """
        self.iterable = iterable
        self.total = total if total is not None else len(iterable) if iterable else None
        self.desc = desc or ""
        self.mininterval = mininterval
        self.logger_level = logger_level
        self.logging_interval = logging_interval

        self._n = 0
        self._start_time = time.time()
        self._last_log_time = 0
        self._last_log_n = 0
        self._postfix: Dict[str, Any] = {}
        self._closed = False

    def __iter__(self):
        if self.iterable is None:
            raise ValueError("Iterable must be provided")

        self._start_time = time.time()
        self._last_log_time = self._start_time
        self._last_log_n = 0

        for obj in self.iterable:
            yield obj
            self.update(1)

        self.close()

    def update(self, n: int = 1):
        """Обновить прогресс на n шагов"""
        if self._closed:
            return

        self._n += n
        current_time = time.time()

        # Проверка условий логирования
        time_condition = (current_time - self._last_log_time) >= self.mininterval
        step_condition = (
            (self._n - self._last_log_n) >= self.logging_interval
            if isinstance(self.logging_interval, int)
            else (self.total and (self._n / self.total * 100) - (
                        self._last_log_n / self.total * 100) >= self.logging_interval
                  ))

        if time_condition and step_condition:
            self._log_progress()
        self._last_log_n = self._n
        self._last_log_time = current_time

    def set_description(self, desc: Optional[str] = None):
        """Установить описание прогресса"""
        self.desc = desc or ""

    def set_postfix(self, **kwargs):
        """Установить дополнительные параметры для отображения"""
        self._postfix = kwargs

    def _log_progress(self):
        """Сформировать и отправить сообщение о прогрессе"""
        elapsed = time.time() - self._start_time
        rate = self._n / elapsed if elapsed > 0 else 0

        # Форматирование основного сообщения
        if self.total:
            percentage = 100 * self._n / self.total
            remaining = (self.total - self._n) / rate if rate > 0 else 0
            base_msg = (
                f"{self.desc} | {percentage:.1f}% "
                f"({self._n}/{self.total}) "
                f"[elapsed: {elapsed:.1f}s, remaining: {remaining:.1f}s, {rate:.2f} it/s]"
            )
        else:
            base_msg = (
                f"{self.desc} | {self._n} iterations "
                f"[elapsed: {elapsed:.1f}s, {rate:.2f} it/s]"
            )

        # Добавление постфиксных значений
        if self._postfix:
            postfix_str = ", ".join(f"{k}={v}" for k, v in self._postfix.items())
            base_msg += f" | {postfix_str}"

        # Отправка через logger
        logger.log(self.logger_level, base_msg)

    def close(self):
        """Завершить прогресс-бар (вывести финальное сообщение)"""
        if not self._closed:
            self._log_progress()
            self._closed = True

    def __enter__(self):
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def silent_trange(*args, **kwargs) -> SilentTqdm:
    """Аналог tqdm.trange с логированием через loguru"""
    return SilentTqdm(range(*args), **kwargs)