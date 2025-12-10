"""Configuration management for MS Learn Downloader."""

import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration manager for the application."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration from YAML file."""
        self.config_path = Path(config_path)
        self._config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'api': {
                'base_url': 'https://learn.microsoft.com/api/catalog/',
                'content_base_url': 'https://learn.microsoft.com',
                'locale': 'en-us',
                'timeout': 30,
                'retry_attempts': 3,
                'retry_delay': 2
            },
            'download': {
                'images': True,
                'include_exercises': True,
                'include_code_samples': True,
                'max_concurrent_downloads': 5
            },
            'output': {
                'default_format': 'pdf',
                'create_toc': True,
                'include_metadata': True,
                'compress_images': False
            },
            'pdf': {
                'include_bookmarks': True,
                'page_size': 'A4',
                'margin': '2cm',
                'font_size': '11pt',
                'syntax_highlighting': True
            },
            'storage': {
                'output_dir': './downloads',
                'temp_dir': './temp',
                'cache_dir': './cache'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def set(self, key: str, value: Any):
        """Set configuration value by dot-notation key."""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value
