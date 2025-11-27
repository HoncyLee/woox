# WOOX API Best Practices Implementation Checklist

## ✅ Completed Improvements

### 1. Error Handling ✓
- [x] Created `woox_errors.py` with all WOOX error codes
- [x] Implemented custom exception classes
- [x] Added error code mappings (-1000 to -1103)
- [x] Added order service error codes (317xxx)
- [x] Implemented retry logic for transient errors
- [x] Added user-friendly error formatting

### 2. API Endpoint Corrections ✓
- [x] Verified correct API versions:
  - `/v1/` for most endpoints (orderbook, market_trades, orders)
  - `/v3/` for: balances, algo orders, account info
- [x] Updated Content-Type headers for POST/PUT requests
- [x] Added proper query parameter handling

### 3. Symbol Format ✓
- [x] Using correct format: `SPOT_BTC_USDT` or `PERP_BTC_USDT`
- [x] Verified in CONFIG and all API calls

## 🔄 In Progress / To Implement

### 4. Order Placement Improvements
- [ ] Add `client_order_id` generation for order tracking
  ```python
  import uuid
  client_order_id = int(str(int(time.time() * 1000))[-12:])  # Last 12 digits
  ```

- [ ] Add `order_tag` for organization (default: "default")
  ```python
  order_tag = CONFIG.get('ORDER_TAG', 'algo_bot')
  ```

- [ ] Convert numeric values to strings for precision
  ```python
  data = {
      "order_price": str(price),  # Not float
      "order_quantity": str(quantity)  # Not float
  }
  ```

- [ ] Add `reduce_only` parameter for risk management
  ```python
  reduce_only = False  # Set True to only reduce positions
  ```

- [ ] Add `visible_quantity` for iceberg orders
  ```python
  visible_quantity = quantity  # Or less for hidden orders
  ```

### 5. Request/Response Handling
- [ ] Add comprehensive error handling wrapper
  ```python
  from woox_errors import handle_api_error, is_retryable_error
  
  try:
      response = requests.post(url, json=data, headers=headers)
      response_json = response.json()
      handle_api_error(response_json, self.logger)
  except WooxRateLimitError as e:
      # Implement exponential backoff
      pass
  ```

- [ ] Implement retry mechanism with exponential backoff
  ```python
  from woox_errors import get_retry_delay
  
  max_retries = 3
  for attempt in range(max_retries):
      try:
          # Make request
          break
      except WooxRateLimitError as e:
          if attempt < max_retries - 1:
              delay = get_retry_delay(e.code, attempt)
              time.sleep(delay)
  ```

- [ ] Add response validation
  ```python
  if not response_json.get('success'):
      handle_api_error(response_json, self.logger)
  ```

### 6. Rate Limiting
- [ ] Implement request rate tracking
  ```python
  # Track requests per second
  self.request_timestamps = deque(maxlen=100)
  
  def check_rate_limit(self, endpoint_limit: int = 10):
      current_time = time.time()
      self.request_timestamps.append(current_time)
      recent = [ts for ts in self.request_timestamps if current_time - ts < 1]
      if len(recent) >= endpoint_limit:
          time.sleep(1 - (current_time - recent[0]))
  ```

- [ ] Add per-endpoint rate limits
  - GET requests: 10/second (most endpoints)
  - POST orders: 10/second per symbol
  - Private endpoints: Based on account limits

### 7. WebSocket Integration (Recommended)
- [ ] Replace REST polling with WebSocket for real-time data
  ```python
  # Connect to WebSocket
  wss://wss.woox.io/ws/stream/{application_id}
  
  # Subscribe to topics:
  {
      "id": "client_1",
      "event": "subscribe",
      "topic": "SPOT_BTC_USDT@orderbookupdate"  # 200ms updates
  }
  ```

- [ ] Implement WebSocket topics:
  - `{symbol}@orderbookupdate` - Real-time orderbook (200ms)
  - `{symbol}@trade` - Real-time trades
  - `executionreport` - Order status updates
  - `balance` - Balance updates
  - `position` - Position updates

### 8. Order Types and Parameters
- [ ] Implement all order types properly:
  - `MARKET` - Matches until filled or cancelled
  - `LIMIT` - Standard limit order
  - `POST_ONLY` - Only maker orders
  - `IOC` - Immediate or Cancel
  - `FOK` - Fill or Kill
  - `ASK`/`BID` - Best ask/bid price

- [ ] Add position management:
  ```python
  # For futures/perpetual
  position_side = "LONG" | "SHORT" | "BOTH"  # Hedge mode vs One-way
  margin_mode = "CROSS" | "ISOLATED"
  leverage = 10  # Set appropriately
  ```

### 9. Data Type Precision
- [ ] Ensure all numeric values use strings in API requests
  ```python
  # ❌ Wrong
  {"price": 50000.50, "quantity": 0.001}
  
  # ✅ Correct
  {"price": "50000.50", "quantity": "0.001"}
  ```

- [ ] Use Decimal for internal calculations
  ```python
  from decimal import Decimal
  
  price = Decimal('50000.50')
  quantity = Decimal('0.001')
  total = price * quantity
  ```

### 10. API Version Consistency
- [ ] Verify all endpoints use correct version:
  ```python
  # V1 Endpoints (most common)
  /v1/public/info/{symbol}  # Exchange info
  /v1/public/market_trades  # Market trades
  /v1/public/orderbook/{symbol}  # Orderbook
  /v1/order  # Send order
  /v1/orders  # Get orders
  
  # V3 Endpoints (newer)
  /v3/balances  # Get balance
  /v3/accountinfo  # Account info
  /v3/algo/order  # Algo orders
  /v3/positions  # Position info
  ```

### 11. Authentication Best Practices
- [ ] Add receive window for VIP users
  ```python
  headers = {
      'x-api-recvwindow': '5000',  # 5 seconds (VIP only)
      # ... other headers
  }
  ```

- [ ] Implement signature caching for identical requests
- [ ] Add timestamp validation (300s max difference)

### 12. Database Improvements
- [ ] Add transaction tracking with `client_order_id`
  ```sql
  ALTER TABLE trades ADD COLUMN client_order_id INTEGER;
  ALTER TABLE trades ADD COLUMN order_id INTEGER;
  ```

- [ ] Store order status updates
  ```sql
  CREATE TABLE order_status (
      order_id INTEGER PRIMARY KEY,
      client_order_id INTEGER,
      status TEXT,
      updated_at TIMESTAMP
  );
  ```

### 13. Logging Enhancements
- [ ] Add request/response logging for debugging
  ```python
  self.logger.debug("Request: %s %s", method, url)
  self.logger.debug("Headers: %s", headers)
  self.logger.debug("Body: %s", body)
  self.logger.debug("Response: %s", response.json())
  ```

- [ ] Add performance metrics
  ```python
  start_time = time.time()
  # ... make request ...
  elapsed = time.time() - start_time
  self.logger.info("API call took %.3fs", elapsed)
  ```

### 14. Configuration Management
- [ ] Add exchange information validation
  ```python
  def validate_symbol_config(self):
      """Validate symbol against exchange info"""
      info = self.get_exchange_info(self.symbol)
      # Check min/max quantity, price filters, etc.
  ```

- [ ] Add price/quantity filters
  ```python
  # From /v1/public/info/{symbol}
  quote_min, quote_max, quote_tick
  base_min, base_max, base_tick
  min_notional
  price_range, price_scope
  ```

### 15. Testing and Validation
- [ ] Add unit tests for error handling
- [ ] Add integration tests with staging API
  ```python
  # Staging endpoint
  https://api.staging.woox.io
  wss://wss.staging.woox.io
  ```

- [ ] Test with paper trading mode thoroughly
- [ ] Validate all order types before live trading

## 📋 Priority Implementation Order

1. **Critical (Do First)**
   - ✅ Error handling (completed)
   - 🔄 Order placement improvements (in progress)
   - 🔄 Response validation
   - 🔄 Rate limiting

2. **High Priority**
   - Data type precision (strings for numbers)
   - Retry mechanism
   - Request/response logging
   - Symbol configuration validation

3. **Medium Priority**
   - WebSocket integration
   - Database improvements
   - Performance metrics
   - client_order_id implementation

4. **Low Priority (Nice to Have)**
   - Advanced order types (algo orders)
   - Position management for futures
   - Comprehensive testing suite

## 🔍 Verification Commands

```bash
# Test API connectivity
curl https://api.woox.io/v1/public/system_info

# Validate symbol format
curl https://api.woox.io/v1/public/info/SPOT_BTC_USDT

# Check orderbook endpoint
curl https://api.woox.io/v1/public/orderbook/SPOT_BTC_USDT

# Test authentication (requires credentials)
# Use your test scripts with proper error handling
```

## 📚 Reference Documentation

- Official API Docs: https://docs.woox.io/
- API Endpoints: `https://api.woox.io`
- WebSocket: `wss://wss.woox.io/ws/stream/{application_id}`
- Staging (for testing): `https://api.staging.woox.io`

## ⚠️ Important Notes

1. **Domain Migration**: WOOX migrated from `woo.org` to `woox.io` on 2024/09/22
   - Old: `api.woo.org` → New: `api.woox.io` ✅
   - Old: `wss.woo.org` → New: `wss.woox.io` ✅

2. **Error Code -1003 (Rate Limit)**
   - Exponential backoff: 2^attempt seconds
   - Max wait: 60 seconds
   - Consider request queuing

3. **Precision Requirements**
   - Always use strings for price/quantity in API requests
   - Use Decimal for calculations
   - Respect symbol's tick sizes

4. **Testing Strategy**
   - Use staging environment first
   - Start with paper trading mode
   - Validate with small amounts in live
   - Monitor error logs closely

## 🎯 Success Metrics

- [ ] Zero authentication errors
- [ ] Proper handling of all error codes
- [ ] Rate limit compliance (no -1003 errors)
- [ ] All orders use string precision
- [ ] Retry mechanism working for transient errors
- [ ] Comprehensive error logging
- [ ] WebSocket integration (optional but recommended)
