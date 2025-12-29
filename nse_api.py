"""
NSE API Wrapper
Custom NSE data fetcher using direct NSE API endpoints.
"""

import requests
from time import sleep
import os
from datetime import datetime, timedelta
import csv


class NSEDataFetcher:
    """
    Custom NSE data fetcher using direct NSE API endpoints.
    Provides live stock prices and options data.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.nseindia.com/'
        }
        self.cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
        self._initialize_session()
        self.lot_sizes = self._load_lot_sizes()
    
    def _initialize_session(self):
        """Get cookies from NSE homepage"""
        try:
            self.session.get("https://www.nseindia.com", headers=self.headers, timeout=10)
            sleep(0.3)  # Be respectful to the server
        except Exception as e:
            print(f"Warning: Could not initialize session: {e}")
    
    def get_derivatives_data(self, symbol):
        """
        Fetch derivatives data for a symbol.
        
        Args:
            symbol (str): Stock symbol (e.g., 'PNB', 'SBIN')
            
        Returns:
            dict: Raw API response containing all derivatives data
        """
        url = f"https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolDerivativesData&symbol={symbol}"
        
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching data for {symbol}: Status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Exception fetching data for {symbol}: {e}")
            return None
    
    def get_stock_price(self, symbol):
        """
        Get current stock price from derivatives data.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            float: Current stock price (underlyingValue)
        """
        data = self.get_derivatives_data(symbol)
        
        if data and 'data' in data and len(data['data']) > 0:
            # underlyingValue is the same across all records
            return data['data'][0].get('underlyingValue', 0)
        return 0
    
    def get_options_data(self, symbol, expiry_month=None):
        """
        Get options (CALL and PUT) data for a symbol.
        
        Args:
            symbol (str): Stock symbol
            expiry_month (str, optional): Filter by expiry month (e.g., 'Jan', 'Feb')
            
        Returns:
            list: List of dictionaries containing options data
        """
        data = self.get_derivatives_data(symbol)
        
        if not data or 'data' not in data:
            return []
        
        options = []
        
        for item in data['data']:
            # Filter for options only (OPTSTK = Stock Options)
            if item.get('instrumentType') == 'OPTSTK':
                option_type = item.get('optionType')  # 'CE' for Call, 'PE' for Put
                expiry_date = item.get('expiryDate', '')
                
                # Extract month from expiry date (format: '30-Dec-2025')
                month = expiry_date.split('-')[1] if '-' in expiry_date else ''
                
                # Filter by expiry month if specified
                if expiry_month and month != expiry_month:
                    continue
                
                # Extract strike price (format: '     120.00' with spaces)
                strike_str = item.get('strikePrice', '0').strip()
                strike = float(strike_str) if strike_str else 0
                
                options.append({
                    'symbol': symbol,
                    'expiry_date': expiry_date,
                    'expiry_month': month,
                    'option_type': option_type,  # 'CE' or 'PE'
                    'strike': strike,
                    'last_price': item.get('lastPrice', 0),
                    'volume': item.get('totalTradedVolume', 0),
                    'open_interest': item.get('openInterest', 0),
                    'underlying_value': item.get('underlyingValue', 0)
                })
        
        return options
    
    def _download_lot_sizes(self):
        """
        Download the latest lot sizes CSV from NSE.
        Saves to cache directory with today's date.
        
        Returns:
            str: Path to downloaded file, or None if download failed
        """
        url = 'https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv'
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Generate filename with today's date
        today = datetime.now().strftime('%Y-%m-%d')
        cache_file = os.path.join(self.cache_dir, f'fo_mktlots_{today}.csv')
        
        try:
            print(f"Downloading lot sizes from NSE...")
            response = self.session.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                with open(cache_file, 'wb') as f:
                    f.write(response.content)
                print(f"✓ Lot sizes cached: {cache_file}")
                
                # Clean up old cache files (older than 7 days)
                self._cleanup_old_cache()
                
                return cache_file
            else:
                print(f"⚠️  Failed to download lot sizes: Status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"⚠️  Error downloading lot sizes: {e}")
            return None
    
    def _cleanup_old_cache(self):
        """
        Remove cache files older than 7 days.
        """
        if not os.path.exists(self.cache_dir):
            return
        
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for filename in os.listdir(self.cache_dir):
            if filename.startswith('fo_mktlots_') and filename.endswith('.csv'):
                filepath = os.path.join(self.cache_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_time < cutoff_date:
                    try:
                        os.remove(filepath)
                        print(f"✓ Cleaned old cache: {filename}")
                    except Exception as e:
                        print(f"⚠️  Could not remove old cache {filename}: {e}")
    
    def _load_lot_sizes(self):
        """
        Load lot sizes from cache or download if needed.
        Only uses cache files that are less than 7 days old.
        Raises an error if no valid lot sizes can be obtained.
        
        Returns:
            dict: {symbol: lot_size}
        
        Raises:
            RuntimeError: If lot sizes cannot be loaded from cache or downloaded
        """
        # Check for today's cache file
        today = datetime.now().strftime('%Y-%m-%d')
        cache_file = os.path.join(self.cache_dir, f'fo_mktlots_{today}.csv')
        cutoff_date = datetime.now() - timedelta(days=7)
        
        # If today's cache doesn't exist, try to find a recent cache (< 7 days old)
        if not os.path.exists(cache_file):
            if os.path.exists(self.cache_dir):
                cache_files = []
                for f in os.listdir(self.cache_dir):
                    if f.startswith('fo_mktlots_') and f.endswith('.csv'):
                        filepath = os.path.join(self.cache_dir, f)
                        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                        # Only consider files less than 7 days old
                        if file_time >= cutoff_date:
                            cache_files.append((f, file_time))
                
                if cache_files:
                    # Use most recent valid cache file
                    cache_files.sort(key=lambda x: x[1], reverse=True)
                    cache_file = os.path.join(self.cache_dir, cache_files[0][0])
                    print(f"Using cached lot sizes: {cache_files[0][0]}")
                else:
                    # No valid cache exists, download new
                    cache_file = self._download_lot_sizes()
            else:
                # Cache directory doesn't exist, download new
                cache_file = self._download_lot_sizes()
        else:
            print(f"Using today's cached lot sizes")
        
        # Parse the CSV file
        lot_sizes = {}
        
        if cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    
                    if len(rows) > 0:
                        # First row is headers
                        headers = [h.strip() for h in rows[0]]
                        
                        # Column 1 is SYMBOL, columns 2+ are month lot sizes
                        symbol_col_idx = 1
                        month_col_start = 2
                        
                        # Parse each row
                        for row in rows[1:]:  # Skip header
                            if len(row) > symbol_col_idx:
                                symbol = row[symbol_col_idx].strip()
                                
                                # Skip empty or header-like rows
                                if not symbol or symbol == 'Symbol':
                                    continue
                                
                                # Find first non-empty lot size from month columns
                                lot_size = None
                                for col_idx in range(month_col_start, len(row)):
                                    value = row[col_idx].strip()
                                    if value and value.isdigit():
                                        lot_size = int(value)
                                        break  # Use first available month
                                
                                if lot_size:
                                    lot_sizes[symbol] = lot_size
                
                print(f"✓ Loaded {len(lot_sizes)} lot sizes from cache")
                
            except Exception as e:
                print(f"⚠️  Error parsing lot sizes CSV: {e}")
        
        # If no lot sizes were loaded, raise an error
        if not lot_sizes:
            raise RuntimeError(
                "Cannot find lot sizes. "
                "No valid cache available (must be less than 7 days old) "
                "and unable to download from NSE. "
                "Please check your internet connection and try again."
            )
        
        return lot_sizes
    
    def get_lot_size(self, symbol):
        """
        Get lot size for a symbol from cached data.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            int: Lot size for the symbol
            
        Raises:
            ValueError: If symbol not found in lot sizes cache
        """
        if symbol not in self.lot_sizes:
            raise ValueError(
                f"Lot size not found for symbol '{symbol}'. "
                f"Symbol may not be available for F&O trading or may not be in the NSE lot sizes CSV."
            )
        return self.lot_sizes[symbol]
