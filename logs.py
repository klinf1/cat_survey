import logging
import logging.handlers

def get_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        "cat_log.log", maxBytes=50000000, backupCount=5
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s - %(lineno)s - %(funcName)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
