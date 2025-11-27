Error Handling & Best Practices
================================

This page documents the production-grade error handling system and best practices for using the WOOX API.

Overview
--------

The bot includes comprehensive error handling following WOOX official documentation standards:

* **40+ Error Codes Mapped**: Complete coverage of WOOX API errors
* **Exception Hierarchy**: Specialized exceptions for different error types
* **Automatic Retry Logic**: Exponential backoff for rate limits
* **Error Formatting**: User-friendly messages and detailed logging

Error Code Reference
--------------------

Standard API Errors (-1000 to -1103)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 50 35

   * - Error Code
     - Description
     - Exception Type
   * - -1000
     - Invalid signature
     - WooxAuthenticationError
   * - -1001
     - Invalid timestamp
     - WooxAuthenticationError
   * - -1002
     - Invalid API key
     - WooxAuthenticationError
   * - -1003
     - Too many requests (rate limit)
     - WooxRateLimitError
   * - -1004
     - Missing required parameter
     - WooxInvalidParameterError
   * - -1005
     - Invalid parameter value
     - WooxInvalidParameterError
   * - -1006
     - Invalid symbol
     - WooxInvalidParameterError
   * - -1007
     - Invalid order type
     - WooxInvalidParameterError
   * - -1008
     - Invalid side
     - WooxInvalidParameterError
   * - -1009
     - Invalid quantity
     - WooxInvalidParameterError
   * - -1010
     - Invalid price
     - WooxInvalidParameterError
   * - -1011
     - Resource not found
     - WooxResourceNotFoundError
   * - -1012
     - Service unavailable
     - WooxServerError

Order Service Errors (317xxx)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 50 35

   * - Error Code
     - Description
     - Common Cause
   * - 317136
     - Repeated client_order_id
     - Duplicate order ID
   * - 317137
     - Invalid client_order_id format
     - Wrong format (must be int64)
   * - 317143
     - Invalid order_quantity
     - Quantity below minimum
   * - 317144
     - Invalid order_price
     - Price below minimum
   * - 317145
     - Invalid notional value
     - Price × Quantity too small
   * - 317201
     - Insufficient balance
     - Not enough funds
   * - 317202
     - Quantity below minimum
     - Check symbol's base_min
   * - 317203
     - Quantity above maximum
     - Check symbol's base_max
   * - 317204
     - Price below minimum
     - Check symbol's quote_min
   * - 317205
     - Price above maximum
     - Check symbol's quote_max

For complete error code list, see ``woox_errors.ERROR_CODES`` and ``woox_errors.ORDER_ERROR_CODES``.

Exception Hierarchy
-------------------

All WOOX API errors inherit from ``WooxError``:

.. code-block:: text

   WooxError (base)
   ├── WooxAuthenticationError
   │   └── Invalid API key, signature, or timestamp
   ├── WooxRateLimitError
   │   └── Too many requests (-1003)
   ├── WooxInvalidParameterError
   │   └── Invalid parameters (-1004 to -1010)
   ├── WooxResourceNotFoundError
   │   └── Order or resource not found (-1011)
   └── WooxServerError
       └── Server errors (-1012, -1099 to -1103)

Usage Examples
--------------

Basic Error Handling
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from woox_errors import WooxError, handle_api_error, ErrorFormatter
   import requests

   try:
       response = requests.post(url, headers=headers, json=data)
       if response.status_code != 200:
           handle_api_error(response)
       
       result = response.json()
       
   except WooxError as e:
       # Log the error
       logger.error(ErrorFormatter.format_error(e))
       # Show user-friendly message
       print(ErrorFormatter.format_user_message(e))

Specific Exception Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from woox_errors import (
       WooxAuthenticationError,
       WooxRateLimitError,
       WooxInvalidParameterError,
       WooxServerError
   )

   try:
       # Place order
       response = place_order(symbol, side, price, quantity)
       
   except WooxAuthenticationError as e:
       logger.error("Authentication failed: %s", e)
       # Check API key and secret
       
   except WooxRateLimitError as e:
       logger.warning("Rate limited: %s", e)
       # Reduce request frequency
       
   except WooxInvalidParameterError as e:
       logger.error("Invalid parameters: %s", e)
       # Validate order parameters
       
   except WooxServerError as e:
       logger.error("Server error: %s", e)
       # Retry later

Retry Logic
-----------

Automatic Retry with Exponential Backoff
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The bot automatically retries certain errors:

.. code-block:: python

   from woox_errors import is_retryable_error, get_retry_delay

   max_retries = 3
   attempt = 0
   
   while attempt < max_retries:
       try:
           response = make_request()
           if response.status_code == 200:
               break
               
           error_code = response.json().get('code')
           if not is_retryable_error(error_code):
               handle_api_error(response)
               break
               
       except Exception as e:
           if attempt >= max_retries - 1:
               raise
           
           delay = get_retry_delay(error_code, attempt)
           logger.warning(f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
           time.sleep(delay)
           attempt += 1

Retryable Errors
~~~~~~~~~~~~~~~~

The following errors trigger automatic retry:

* **-1000**: Invalid signature (may be timing issue)
* **-1003**: Rate limit exceeded
* **-1011**: Resource not found (may be propagation delay)
* **-1012**: Service unavailable

Retry delays:

* **Rate limits (-1003)**: Exponential backoff (2^attempt, max 60s)
* **Server errors (-1012)**: Linear backoff (attempt × 5, max 30s)
* **Other retryable**: Linear backoff (attempt × 2, max 10s)

Best Practices
--------------

1. Always Use Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Never make API calls without proper error handling:

.. code-block:: python

   # ❌ BAD - No error handling
   response = requests.get(url)
   data = response.json()
   
   # ✅ GOOD - Proper error handling
   try:
       response = requests.get(url, timeout=10)
       if response.status_code != 200:
           handle_api_error(response)
       data = response.json()
   except WooxError as e:
       logger.error(ErrorFormatter.format_error(e))
       raise

2. Use Centralized Request Method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a reusable request method with error handling:

.. code-block:: python

   def _make_request(self, method, endpoint, params=None, data=None):
       """Make API request with error handling and retry logic."""
       url = f"{self.base_url}{endpoint}"
       max_retries = 3
       
       for attempt in range(max_retries):
           try:
               response = requests.request(
                   method=method,
                   url=url,
                   headers=self._get_auth_headers(method, endpoint, data),
                   params=params,
                   json=data,
                   timeout=10
               )
               
               if response.status_code == 200:
                   return response.json()
               
               error_code = response.json().get('code')
               if not is_retryable_error(error_code):
                   handle_api_error(response)
                   return None
               
               if attempt < max_retries - 1:
                   delay = get_retry_delay(error_code, attempt)
                   logger.warning(f"Retry in {delay}s (attempt {attempt + 1})")
                   time.sleep(delay)
               else:
                   handle_api_error(response)
                   
           except requests.RequestException as e:
               logger.error("Request failed: %s", str(e))
               if attempt >= max_retries - 1:
                   raise

3. Validate Before Sending
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use OrderHelper to validate orders before submission:

.. code-block:: python

   from order_helper import OrderHelper

   order_helper = OrderHelper(logger)
   
   # Get symbol info (cache this in production)
   symbol_info = {
       'quote_min': 0,
       'quote_max': 100000,
       'quote_tick': 0.01,
       'base_min': 0.0001,
       'base_max': 20,
       'base_tick': 0.0001,
       'min_notional': 10
   }
   
   # Validate before placing order
   if not order_helper.validate_price_filters(price, symbol_info):
       logger.error("Invalid price")
       return
       
   if not order_helper.validate_quantity_filters(quantity, symbol_info):
       logger.error("Invalid quantity")
       return
       
   if not order_helper.validate_min_notional(price, quantity, symbol_info):
       logger.error("Notional value too small")
       return

4. Use Proper Number Formatting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Always format numbers as strings for API requests:

.. code-block:: python

   from order_helper import OrderHelper

   order_helper = OrderHelper(logger)
   
   # ❌ BAD - Float precision issues
   order_data = {
       "order_price": 50123.456789,  # May lose precision
       "order_quantity": 0.001234567890
   }
   
   # ✅ GOOD - String with proper precision
   order_data = {
       "order_price": order_helper.format_price(50123.456789),
       "order_quantity": order_helper.format_quantity(0.001234567890)
   }
   # Result: {"order_price": "50123.45678901", "order_quantity": "0.00123456"}

5. Track Client Order IDs
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use unique client order IDs for tracking:

.. code-block:: python

   from order_helper import OrderHelper

   order_helper = OrderHelper(logger)
   
   order_data = order_helper.create_limit_order(
       symbol="SPOT_BTC_USDT",
       side="BUY",
       price=50000.00,
       quantity=0.001,
       order_tag="algo_bot"
   )
   
   # order_data includes unique client_order_id
   # Store in database for reconciliation
   client_order_id = order_data['client_order_id']

6. Log Errors Appropriately
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use different log levels for different scenarios:

.. code-block:: python

   try:
       result = place_order(...)
       
   except WooxRateLimitError as e:
       # Warning for rate limits (expected in high-frequency)
       logger.warning("Rate limited: %s", ErrorFormatter.format_user_message(e))
       
   except WooxInvalidParameterError as e:
       # Error for validation issues (should be prevented)
       logger.error("Invalid parameters: %s", ErrorFormatter.format_error(e))
       
   except WooxServerError as e:
       # Error for server issues (needs attention)
       logger.error("Server error: %s", ErrorFormatter.format_error(e))
       
   except WooxError as e:
       # Catch-all for other errors
       logger.error("Unexpected error: %s", ErrorFormatter.format_error(e))

7. Respect Rate Limits
~~~~~~~~~~~~~~~~~~~~~~~

Implement rate limiting to prevent -1003 errors:

.. code-block:: python

   import time
   from collections import deque

   class RateLimiter:
       def __init__(self, max_requests=10, time_window=1.0):
           self.max_requests = max_requests
           self.time_window = time_window
           self.requests = deque()
       
       def check_limit(self):
           now = time.time()
           # Remove old requests
           while self.requests and self.requests[0] < now - self.time_window:
               self.requests.popleft()
           
           # Check if limit reached
           if len(self.requests) >= self.max_requests:
               wait_time = self.requests[0] + self.time_window - now
               if wait_time > 0:
                   time.sleep(wait_time)
           
           self.requests.append(now)

Testing Error Handling
-----------------------

Test different error scenarios:

.. code-block:: python

   # Test authentication error
   def test_invalid_signature():
       try:
           trader = Trade(api_key="invalid", api_secret="invalid")
           trader.get_balance()
       except WooxAuthenticationError as e:
           print(f"✅ Caught authentication error: {e}")
   
   # Test rate limit
   def test_rate_limit():
       trader = Trade()
       for i in range(20):  # Trigger rate limit
           try:
               trader.trade_update()
           except WooxRateLimitError as e:
               print(f"✅ Caught rate limit at request {i}: {e}")
               break
   
   # Test invalid parameters
   def test_invalid_parameters():
       try:
           order = order_helper.create_limit_order(
               symbol="INVALID_SYMBOL",
               side="INVALID",
               price=-100,
               quantity=0
           )
       except WooxInvalidParameterError as e:
           print(f"✅ Caught invalid parameters: {e}")

Monitoring and Alerting
------------------------

Set up monitoring for production:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler
   
   # Setup error logging
   error_handler = RotatingFileHandler(
       'errors.log',
       maxBytes=10485760,  # 10MB
       backupCount=5
   )
   error_handler.setLevel(logging.ERROR)
   error_formatter = logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   error_handler.setFormatter(error_formatter)
   logger.addHandler(error_handler)
   
   # Track error counts
   error_counts = {}
   
   def log_error_with_tracking(error_code, error_message):
       error_counts[error_code] = error_counts.get(error_code, 0) + 1
       logger.error(f"Error {error_code} (count: {error_counts[error_code]}): {error_message}")
       
       # Alert on threshold
       if error_counts[error_code] > 10:
           send_alert(f"High error count for {error_code}")

See Also
--------

* :doc:`api_reference` - Complete API documentation
* :doc:`testing` - Testing guide
* ``woox_errors.py`` - Error handling implementation
* ``order_helper.py`` - Order validation and formatting
* ``examples_best_practices.py`` - Usage examples
* ``WOOX_BEST_PRACTICES_CHECKLIST.md`` - Implementation checklist
