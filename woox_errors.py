"""
WOOX API Error Codes and Exception Handling.
Based on official WOOX API documentation.
"""
from typing import Optional, Dict, Any
import logging


class WooxError(Exception):
    """Base exception for WOOX API errors."""
    
    def __init__(self, code: int, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class WooxAuthenticationError(WooxError):
    """Authentication-related errors."""
    pass


class WooxRateLimitError(WooxError):
    """Rate limit exceeded."""
    pass


class WooxInvalidParameterError(WooxError):
    """Invalid parameter in request."""
    pass


class WooxResourceNotFoundError(WooxError):
    """Requested resource not found."""
    pass


class WooxServerError(WooxError):
    """Internal server error."""
    pass


# WOOX API Error Code Mappings
ERROR_CODES = {
    # General Errors
    -1000: {
        'name': 'UNKNOWN',
        'description': 'An unknown error occurred while processing the request',
        'http_code': 500,
        'exception': WooxServerError
    },
    -1001: {
        'name': 'INVALID_SIGNATURE',
        'description': 'The api key or secret is in wrong format',
        'http_code': 401,
        'exception': WooxAuthenticationError
    },
    -1002: {
        'name': 'UNAUTHORIZED',
        'description': 'API key or secret is invalid, insufficient permissions or expired/revoked',
        'http_code': 401,
        'exception': WooxAuthenticationError
    },
    -1003: {
        'name': 'TOO_MANY_REQUEST',
        'description': 'Rate limit exceeded',
        'http_code': 429,
        'exception': WooxRateLimitError
    },
    -1004: {
        'name': 'UNKNOWN_PARAM',
        'description': 'An unknown parameter was sent',
        'http_code': 400,
        'exception': WooxInvalidParameterError
    },
    -1005: {
        'name': 'INVALID_PARAM',
        'description': 'Some parameters are in the wrong format for API',
        'http_code': 400,
        'exception': WooxInvalidParameterError
    },
    -1006: {
        'name': 'RESOURCE_NOT_FOUND',
        'description': 'The data is not found in the server',
        'http_code': 400,
        'exception': WooxResourceNotFoundError
    },
    -1007: {
        'name': 'DUPLICATE_REQUEST',
        'description': 'The data already exists or your request is duplicated',
        'http_code': 409,
        'exception': WooxError
    },
    -1008: {
        'name': 'QUANTITY_TOO_HIGH',
        'description': 'The quantity of settlement is higher than you can request',
        'http_code': 400,
        'exception': WooxInvalidParameterError
    },
    -1009: {
        'name': 'CAN_NOT_WITHDRAWAL',
        'description': 'Cannot request withdrawal settlement, need to deposit other arrears first',
        'http_code': 400,
        'exception': WooxError
    },
    -1011: {
        'name': 'RPC_NOT_CONNECT',
        'description': 'Cannot place/cancel orders due to internal network error',
        'http_code': 400,
        'exception': WooxServerError
    },
    -1012: {
        'name': 'RPC_REJECT',
        'description': 'Request rejected by internal module (liquidation or other internal errors)',
        'http_code': 400,
        'exception': WooxServerError
    },
    -1101: {
        'name': 'RISK_TOO_HIGH',
        'description': 'Risk exposure too high (order too big or leverage too low)',
        'http_code': 400,
        'exception': WooxError
    },
    -1103: {
        'name': 'INVALID_PRICE_QUOTE_MIN',
        'description': 'The order does not meet the price filter requirement',
        'http_code': 400,
        'exception': WooxInvalidParameterError
    },
}

# Order Service Specific Error Codes (commonly encountered)
ORDER_ERROR_CODES = {
    317136: 'Edit tpsl quantity is not allowed for quantity bracket',
    317137: 'Edit quantity should edit both legs',
    317138: 'Edit quantity should be same for both legs',
    317139: 'Trigger price of 1st leg should not be empty for STOP_BRACKET',
    317140: 'The quantity of a quantity TP/SL order should not be empty',
    317144: 'IndexPrice is not supported for non spot symbol',
    317157: 'Trading with this pair is temporarily suspended',
    317159: 'This pair is currently not supported',
    317160: 'The order id and symbol are not matched',
    317161: 'The order is completed',
    317162: 'The params should not be null or 0',
    317163: 'Cannot edit TP/SL quantity under bracket order',
    317164: 'Invalid client order id',
    317165: 'Invalid order id list',
    317166: 'Invalid client order id list',
    317167: 'Unsupported algo type',
    317168: 'Order failed due to internal service error',
    317170: 'The order quantity must bigger than the executed quantity',
    317172: 'The userId should not be null or 0',
    317173: 'The orderId should not be null or 0',
    317174: 'The order is processing',
    317176: 'The trigger after should from 0 to maxTriggerAfter',
    317177: 'Order has terminated',
    317178: 'The receive window is invalid',
    317179: 'Request has failed as the receive window is exceeded',
    317184: 'The order cannot be found, or it is already completed',
    317206: 'Spot trading is disabled while futures credits are active',
    317207: 'Ensure sufficient USDT to cover futures credits',
}


def get_error_info(code: int) -> Dict[str, Any]:
    """
    Get error information by error code.
    
    Args:
        code: Error code from API response
        
    Returns:
        Dictionary with error details
    """
    if code in ERROR_CODES:
        return ERROR_CODES[code]
    
    # Check order service errors
    if code in ORDER_ERROR_CODES:
        return {
            'name': f'ORDER_ERROR_{code}',
            'description': ORDER_ERROR_CODES[code],
            'http_code': 400,
            'exception': WooxInvalidParameterError
        }
    
    # Unknown error code
    return {
        'name': 'UNKNOWN_ERROR',
        'description': f'Unknown error code: {code}',
        'http_code': 500,
        'exception': WooxError
    }


def handle_api_error(response_data: Dict[str, Any], logger: Optional[logging.Logger] = None) -> None:
    """
    Handle API error response and raise appropriate exception.
    
    Args:
        response_data: JSON response from API
        logger: Optional logger instance
        
    Raises:
        Appropriate WooxError subclass based on error code
    """
    if not response_data.get('success', True):
        code = response_data.get('code', -1000)
        message = response_data.get('message', 'Unknown error')
        
        error_info = get_error_info(code)
        exception_class = error_info.get('exception', WooxError)
        
        if logger:
            logger.error(
                "WOOX API Error - Code: %d, Name: %s, Message: %s",
                code, error_info['name'], message
            )
        
        raise exception_class(code, message, response_data)


def is_retryable_error(code: int) -> bool:
    """
    Check if an error is retryable.
    
    Args:
        code: Error code
        
    Returns:
        True if error is retryable (rate limit, network, server errors)
    """
    retryable_codes = {-1000, -1003, -1011, -1012}
    return code in retryable_codes


def get_retry_delay(code: int, attempt: int = 1) -> float:
    """
    Get suggested retry delay in seconds.
    
    Args:
        code: Error code
        attempt: Current retry attempt number
        
    Returns:
        Delay in seconds
    """
    if code == -1003:  # Rate limit
        return min(60, 2 ** attempt)  # Exponential backoff, max 60s
    elif code in {-1011, -1012}:  # Server errors
        return min(10, 2 * attempt)  # Linear backoff, max 10s
    else:
        return 1.0


class ErrorFormatter:
    """Format error messages for logging and user display."""
    
    @staticmethod
    def format_error(error: WooxError) -> str:
        """
        Format error for logging.
        
        Args:
            error: WooxError instance
            
        Returns:
            Formatted error string
        """
        error_info = get_error_info(error.code)
        return (
            f"WOOX API Error\n"
            f"  Code: {error.code}\n"
            f"  Type: {error_info['name']}\n"
            f"  HTTP: {error_info['http_code']}\n"
            f"  Message: {error.message}\n"
            f"  Description: {error_info['description']}"
        )
    
    @staticmethod
    def format_user_message(error: WooxError) -> str:
        """
        Format user-friendly error message.
        
        Args:
            error: WooxError instance
            
        Returns:
            User-friendly error message
        """
        if isinstance(error, WooxAuthenticationError):
            return "Authentication failed. Please check your API credentials."
        elif isinstance(error, WooxRateLimitError):
            return "Rate limit exceeded. Please wait before retrying."
        elif isinstance(error, WooxInvalidParameterError):
            return f"Invalid request: {error.message}"
        elif isinstance(error, WooxResourceNotFoundError):
            return f"Resource not found: {error.message}"
        else:
            return f"An error occurred: {error.message}"
