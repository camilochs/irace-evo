"""
Centralized logging configuration for irace-evo

This module ensures that logging is configured only once across all modules
to prevent duplicate log messages.
"""

import logging
import sys

# Global flag to track if logging has been initialized
_logging_initialized = False

def setup_logging(level=logging.INFO, format_string=None):
    """
    Setup centralized logging configuration for all irace-evo modules.
    
    This function should be called once at the beginning of the program
    to initialize logging. Subsequent calls will be ignored.
    
    Args:
        level: Logging level (default: logging.INFO)
        format_string: Custom format string (optional)
    """
    global _logging_initialized
    
    if _logging_initialized:
        return  # Already initialized, skip
    
    # Clear any existing handlers from the root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set up basic configuration
    if format_string is None:
        format_string = '%(levelname)s:%(name)s:%(message)s'
    
    # Configure basic logging
    logging.basicConfig(
        level=level,
        format=format_string,
        stream=sys.stdout,
        force=True  # Force reconfiguration
    )
    
    # Prevent duplicate messages by ensuring proper propagation settings
    # for specific loggers that we know might cause issues
    problematic_loggers = [
        'code_manager',
        'llm_service', 
        'compilation',
        'dynamic_prompting',
        'language_handlers'
    ]
    
    for logger_name in problematic_loggers:
        logger = logging.getLogger(logger_name)
        logger.propagate = True  # Let them propagate to avoid creating separate handlers
        # Remove any handlers that might have been added elsewhere
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    _logging_initialized = True


def get_logger(name):
    """
    Get a logger for the given name.
    
    This function ensures that logging is set up before returning the logger.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger instance
    """
    # Ensure logging is initialized
    if not _logging_initialized:
        setup_logging()
    
    logger = logging.getLogger(name)
    
    # Ensure this logger doesn't have its own handlers to prevent duplication
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Ensure proper propagation
    logger.propagate = True
    
    return logger


def reset_logging():
    """
    Reset the logging configuration.
    
    This is useful for testing or when you need to reinitialize logging.
    """
    global _logging_initialized
    _logging_initialized = False
    
    # Clear all handlers from all loggers
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Clear root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)