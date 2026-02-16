import logging
from logging.handlers import TimedRotatingFileHandler
import os

def setup_logger():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "bot.log"),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    handler.suffix = "%Y-%m-%d"  # формат добавляемой даты в имени файла
    handler.setFormatter(formatter)

    # Удаляем старые обработчики (если есть)
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(handler)

    return logger