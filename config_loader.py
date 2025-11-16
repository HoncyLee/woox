"""
Configuration loader for WOOX Trading Bot.
Reads settings from .config file in the project root.
"""
import os
from typing import Dict, Any


def load_config(config_path: str = '.config') -> Dict[str, Any]:
    """
    Load configuration from .config file.
    
    Args:
        config_path: Path to the configuration file (default: .config)
        
    Returns:
        Dictionary containing configuration key-value pairs
    """
    config = {}
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_dir, config_path)
    
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Configuration file not found: {full_path}")
    
    with open(full_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Convert numeric values
                if value.replace('.', '', 1).isdigit():
                    value = float(value) if '.' in value else int(value)
                
                config[key] = value
    
    return config


def get_config_value(key: str, default: Any = None, config_path: str = '.config') -> Any:
    """
    Get a specific configuration value.
    
    Args:
        key: Configuration key to retrieve
        default: Default value if key not found
        config_path: Path to the configuration file
        
    Returns:
        Configuration value or default
    """
    try:
        config = load_config(config_path)
        return config.get(key, default)
    except FileNotFoundError:
        return default


# Load configuration on module import
try:
    CONFIG = load_config()
except FileNotFoundError:
    # If config file doesn't exist, use empty dict
    CONFIG = {}

# Override with environment variables for API credentials (priority to .zshrc)
if os.environ.get('WOOX_API_KEY'):
    CONFIG['WOOX_API_KEY'] = os.environ.get('WOOX_API_KEY')
if os.environ.get('WOOX_API_SECRET'):
    CONFIG['WOOX_API_SECRET'] = os.environ.get('WOOX_API_SECRET')
if os.environ.get('TRADE_MODE'):
    CONFIG['TRADE_MODE'] = os.environ.get('TRADE_MODE')
