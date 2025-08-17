import datetime
from typing import Any, TextIO

elog: TextIO = open("error_log.txt", "a+", encoding="utf-8")
log: TextIO = open("log.txt", "a+", encoding="utf-8")


def _ts() -> str:
    now = datetime.datetime.now()
    return f"{now.date()} {now.timetz()}"


def eLog(error: Any) -> None:
    elog.write(f"[{_ts()}] ERROR: {str(error)}\n")
    elog.flush()
    print(f"[{_ts()}] ERROR: {str(error)}\n")


def Log(action: Any) -> None:
    log.write(f"[{_ts()}] INFO: {str(action)}\n")
    log.flush()
    print(f"[{_ts()}] INFO: {str(action)}\n")
