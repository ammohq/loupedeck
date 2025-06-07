"""
Logging module for PyLoupe.

This module provides a consistent logging interface for the PyLoupe library.
It configures logging with appropriate handlers and formatters.
"""

import logging
import sys
from typing import Optional, Union, Literal

# Define log levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Create a logger
logger = logging.getLogger("pyloupe")
logger.setLevel(logging.INFO)  # Default level

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(console_handler)

def set_log_level(level: Union[LogLevel, int]) -> None:
    """
    Set the logging level for the PyLoupe logger.
    
    Args:
        level: The logging level to set. Can be a string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
               or an integer (logging.DEBUG, logging.INFO, etc.)
    """
    if isinstance(level, str):
        level = getattr(logging, level)
    
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

def add_file_handler(filename: str, level: Union[LogLevel, int] = "INFO") -> None:
    """
    Add a file handler to the PyLoupe logger.
    
    Args:
        filename: The name of the log file
        level: The logging level for the file handler
    """
    if isinstance(level, str):
        level = getattr(logging, level)
    
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: The name of the logger. If None, returns the root PyLoupe logger.
              If provided, returns a child logger with the given name.
    
    Returns:
        A logger instance
    """
    if name is None:
        return logger
    
    return logger.getChild(name)