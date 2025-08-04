"""Модуль логирования TBPostBot.

Предоставляет две функции для записи логов:
- Log: информационные сообщения (log.txt)
- eLog: ошибки и предупреждения (error_log.txt)

Файлы логов открываются в режиме append и буфер сбрасывается после
каждой записи, что делает записи доступными сразу после вызова.

Стиль docstring: Google.
"""

import datetime
from typing import Any, TextIO

# Публичные файловые дескрипторы логов:
# - log (TextIO): информационный лог.
# - elog (TextIO): лог ошибок/предупреждений.
#
# Единицы:
#   Время фиксируется локальным временем хоста в формате: YYYY-MM-DD HH:MM:SS+TZ
# Ограничения:
#   Ротация/ограничение размера не реализованы — при необходимости используйте внешние инструменты.
elog: TextIO = open("error_log.txt", "a+", encoding="utf-8")
log: TextIO = open("log.txt", "a+", encoding="utf-8")


def _ts() -> str:
    """Сформировать метку времени.

    Returns:
        str: Строка вида "YYYY-MM-DD HH:MM:SS+TZ".

    Examples:
        >>> isinstance(_ts(), str)
        True
    """
    now = datetime.datetime.now()
    return f"{now.date()} {now.timetz()}"


def eLog(error: Any) -> None:
    """Записать ошибку или предупреждение в error_log.txt.

    Args:
        error (Any): Объект ошибки/сообщения; приводится к str.

    Returns:
        None

    Notes:
        Сброс буфера выполняется после каждой записи для немедленной доступности логов.

    Examples:
        >>> eLog("Test error")  # doctest: +SKIP
    """
    elog.write(f"[{_ts()}] {str(error)}\n")
    elog.flush()


def Log(action: Any) -> None:
    """Записать информационное сообщение в log.txt.

    Args:
        action (Any): Объект сообщения; приводится к str.

    Returns:
        None

    Examples:
        >>> Log("Started")  # doctest: +SKIP
    """
    log.write(f"[{_ts()}] {str(action)}\n")
    log.flush()
