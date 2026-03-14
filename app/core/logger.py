# app/core/logger.py
import logging


def get_logger(name: str):
    """
    Creates and configures a standard logger for the application.
    """
    logger = logging.getLogger(name)

    # Prevent adding multiple handlers if the logger already exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        # Define the production log format: Time - Context - Level - Message
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger