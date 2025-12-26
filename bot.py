"""Main entry point for the Discord Job Board Bot."""
import logging
import sys
from pathlib import Path
from database import SQLJobDatabase
from discord_bot import create_bot
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to start the bot."""
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Load job database
        logger.info(f"Loading job database from {Config.DB_PATH}...")
        database = SQLJobDatabase(Config.DB_PATH)
        # database.load_all() # Not needed for SQL
        
        if not database.get_all_jobs():
            logger.error("No job postings loaded! Please check XML files.")
            sys.exit(1)
        
        logger.info(f"Successfully loaded {len(database.get_all_jobs())} job postings")
        logger.info(f"Years available: {', '.join(database.get_years())}")
        
        # Create and start bot
        logger.info("Starting Discord bot...")
        bot = create_bot(database)
        bot.run(Config.DISCORD_BOT_TOKEN)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and ensure all required values are set.")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
