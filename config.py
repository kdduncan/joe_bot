"""Configuration management for the Discord Job Board Bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Bot configuration settings."""
    
    # Discord Bot Token
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    ALLOWED_CHANNEL_ID = os.getenv('ALLOWED_CHANNEL_ID')  # Optional: Restrict to single channel
    
    # Database Configuration
    DB_PATH = os.getenv('DB_PATH', 'jobs.db')
    
    # OpenRouter API Configuration
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    
    # Agent Mode Configuration (default: enabled)
    USE_AGENT_MODE = os.getenv('USE_AGENT_MODE', 'true').lower() == 'true'
    AGENT_MODEL = os.getenv('AGENT_MODEL', 'openai/gpt-oss-120b')
    
    # Bot Settings
    BOT_PREFIX = '@'  # Mention-based, not needed but kept for reference
    EMBED_COLOR = 0x5865F2  # Discord blurple
    MAX_RESULTS_DISPLAY = 25  # Maximum number of results to show in one message
    
    # Query Settings
    QUERY_TIMEOUT = 30  # Maximum seconds to process a query
    
    # Data Update Configuration
    DATA_UPDATE_ENABLED = os.getenv('DATA_UPDATE_ENABLED', 'true').lower() == 'true'
    DATA_UPDATE_HOUR = int(os.getenv('DATA_UPDATE_HOUR', '8'))
    DATA_UPDATE_TIMEZONE = os.getenv('DATA_UPDATE_TIMEZONE', 'America/New_York')
    JOE_XLS_URL = os.getenv('JOE_XLS_URL', 'https://www.aeaweb.org/joe/listings?format=xls')
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN not found in environment variables")
        
        if not os.path.exists(cls.DB_PATH):
            raise ValueError(f"Database file does not exist: {cls.DB_PATH}. Run migrate_data.py first.")
        
        return True
