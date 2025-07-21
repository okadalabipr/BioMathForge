import logging
import sys
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

class BioMathForgeLogger:
    """統一ログシステム"""
    
    def __init__(self, name: str, log_dir: Optional[Path] = None):
        self.sanitized_name = self._sanitize_filename(name)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # コンソール出力
        console_handler = logging.StreamHandler(sys.stdout)
        console_format = logging.Formatter(
            '[%(name)s][%(asctime)s] %(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # ファイル出力
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{self.sanitized_name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_format = logging.Formatter(
                '[%(name)s][%(asctime)s] %(levelname)s: %(message)s'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    @staticmethod
    def _sanitize_filename(name: str, max_length: int = 50) -> str:
        if not name:
            return "unnamed"
        # 1. Remove leading/trailing whitespace
        sanitized = name.strip()
        
        # 2. Replace dangerous characters with safe characters
        dangerous_chars = {
            '<': '_lt_',
            '>': '_gt_', 
            ':': '_colon_',
            '"': '_quote_',
            '/': '_slash_',
            '\\': '_backslash_',
            '|': '_pipe_',
            '?': '_question_',
            '*': '_asterisk_',
            ' ': '_',
            '.': '_',
        }
        
        for char, replacement in dangerous_chars.items():
            sanitized = sanitized.replace(char, replacement)
        
        # 3. Allow only alphanumeric characters, underscores, and hyphens
        sanitized = re.sub(r'[^\w\-_]', '_', sanitized)
        
        # 4. Merge consecutive underscores into single underscore
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # 5. Remove leading and trailing underscores
        sanitized = sanitized.strip('_')
        
        # 6. Length limit
        if len(sanitized) > max_length:
            hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
            max_base_length = max_length - 9  # "_" + 8-character hash
            sanitized = f"{sanitized[:max_base_length]}_{hash_suffix}"
        
        # 7. Check for empty string
        if not sanitized:
            sanitized = "unnamed_log"
        
        return sanitized