"""Discord bot implementation for job board queries."""
import discord
from discord.ext import commands, tasks
import logging
import datetime
from typing import Optional

import pytz

from query_engine import QueryEngine
from database import SQLJobDatabase
from utils import create_embed, create_error_embed, create_stats_embed, create_results_embed
from config import Config
from joe_data_fetcher import JOEDataFetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobBoardBot(commands.Bot):
    """Discord bot for querying job posting data."""
    
    def __init__(self, database: SQLJobDatabase):
        """
        Initialize the bot.
        
        Args:
            database: Loaded job database
        """
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        intents.messages = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        self.database = database
        self.query_engine = QueryEngine(database)
        
        # Initialize data fetcher for scheduled updates
        self.data_fetcher = JOEDataFetcher(
            database, 
            xls_url=Config.JOE_XLS_URL
        )
        
        logger.info("JobBoardBot initialized")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Bot is ready and connected to {len(self.guilds)} server(s)')
        logger.info('------')
        
        # Start scheduled tasks
        if Config.DATA_UPDATE_ENABLED and not self.daily_update.is_running():
            self.daily_update.start()
            logger.info(f"Daily update task started (scheduled for {Config.DATA_UPDATE_HOUR}:00 {Config.DATA_UPDATE_TIMEZONE})")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="@mention me with queries!"
            )
        )
    
    @tasks.loop(time=datetime.time(
        hour=8,  # Default, will be overridden in cog_load
        minute=0,
        tzinfo=pytz.timezone('America/New_York')
    ))
    async def daily_update(self):
        """Run daily data update to fetch new JOE listings."""
        logger.info("Starting daily JOE listings update...")
        try:
            result = await self.data_fetcher.run_daily_update()
            if result['success']:
                logger.info(f"Daily update complete: {result['new_count']} new listings added")
            else:
                logger.error(f"Daily update failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Daily update error: {e}", exc_info=True)
    
    @daily_update.before_loop
    async def before_daily_update(self):
        """Wait until the bot is ready before starting the task."""
        await self.wait_until_ready()
        
        # Reconfigure task time based on config
        tz = pytz.timezone(Config.DATA_UPDATE_TIMEZONE)
        update_time = datetime.time(
            hour=Config.DATA_UPDATE_HOUR,
            minute=0,
            tzinfo=tz
        )
        self.daily_update.change_interval(time=update_time)
        logger.info(f"Daily update configured for {update_time}")
    
    async def on_message(self, message: discord.Message):
        """
        Handle incoming messages.
        
        Args:
            message: The received message
        """
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
            
        # Check channel restriction
        if Config.ALLOWED_CHANNEL_ID:
            try:
                allowed_id = int(Config.ALLOWED_CHANNEL_ID)
                if message.channel.id != allowed_id:
                    return
            except ValueError:
                logger.error("Invalid ALLOWED_CHANNEL_ID configuration")
        
        # Check if bot is mentioned
        is_mention = self.user in message.mentions
        
        # Check if this is a reply to the bot's message
        is_reply_to_bot = False
        if message.reference and message.reference.message_id:
            try:
                replied_to = await message.channel.fetch_message(message.reference.message_id)
                if replied_to.author == self.user:
                    is_reply_to_bot = True
            except:
                pass
        
        if is_mention or is_reply_to_bot:
            await self.handle_query(message)
        
        # Process commands (if any are added later)
        await self.process_commands(message)
    
    async def handle_query(self, message: discord.Message):
        """
        Handle a query from a user.
        
        Args:
            message: The message containing the query
        """
        try:
            # Extract query text (remove bot mention)
            query_text = message.content
            
            # Remove bot mention from query
            for mention in message.mentions:
                query_text = query_text.replace(f'<@{mention.id}>', '')
                query_text = query_text.replace(f'<@!{mention.id}>', '')
            
            query_text = query_text.strip()
            
            if not query_text:
                # No query provided, send help
                embed = create_embed(
                    title="👋 Hello!",
                    description="Mention me with a query to search job postings!\n\n"
                               "Try: `@JoeBot how many jobs in 2024?`\n"
                               "Or: `@JoeBot help` for more examples"
                )
                await message.channel.send(embed=embed)
                return
            
            logger.info(f"Processing query from {message.author}: {query_text}")
            
            # Show typing indicator
            async with message.channel.typing():
                # Process the query
                # Use channel ID as context ID for conversation history
                context_id = str(message.channel.id)
                result = self.query_engine.process_query(query_text, context_id=context_id)
                
                # Create appropriate response
                response_data = self._create_response(query_text, result)
                
                # Check if we have a tuple (response_obj, chart_path)
                response_obj = response_data
                chart_path = None
                
                if isinstance(response_data, tuple):
                    response_obj, chart_path = response_data
                
                # Handle chart attachments
                file = None
                if chart_path:
                    try:
                        file = discord.File(chart_path, filename="chart.png")
                    except Exception as e:
                        logger.error(f"Error preparing chart: {e}")
                
                # Send response (either Embed or str)
                if isinstance(response_obj, str):
                    await message.channel.send(content=response_obj, file=file)
                else:
                    await message.channel.send(embed=response_obj, file=file)
                
                # Clean up temporary chart
                if chart_path and hasattr(self.query_engine, 'agent_orchestrator') and \
                   self.query_engine.agent_orchestrator:
                    self.query_engine.agent_orchestrator.visualization_agent.cleanup_chart(chart_path)
                
                logger.info(f"Sent response for query: {query_text}")
        
        except Exception as e:
            logger.error(f"Error handling query: {e}", exc_info=True)
            embed = create_error_embed(
                f"Sorry, I encountered an error processing your query: {str(e)}\n\n"
                "Please try rephrasing your question or use `@JoeBot help` for examples."
            )
            await message.channel.send(embed=embed)
    
    def _create_response(self, query: str, result: dict):
        """
        Create a Discord response based on query results.
        
        Args:
            query: The original query
            result: Query result dictionary
        
        Returns:
            String (plain text), Discord Embed object, or tuple of (Response, chart_path)
        """
        result_type = result.get('type', 'unknown')
        
        if result_type == 'error':
            return create_error_embed(result.get('message', 'Unknown error')), None
        
        elif result_type == 'count':
            # Count query result
            count = result.get('count', 0)
            message = result.get('message', '')
            filters = result.get('filters', {})
            
            embed = create_embed(
                title="Query Results",
                description=message
            )
            
            # Add filter details
            filter_details = []
            if filters.get('year'):
                filter_details.append(f"**Year:** {filters['year']}")
            if filters.get('institution'):
                filter_details.append(f"**Institution:** {filters['institution']}")
            if filters.get('country'):
                filter_details.append(f"**Country:** {filters['country']}")
            if filters.get('state'):
                filter_details.append(f"**State:** {filters['state']}")
            if filters.get('section'):
                filter_details.append(f"**Type:** {filters['section']}")
            
            if filter_details:
                embed.add_field(
                    name="Filters Applied",
                    value='\n'.join(filter_details),
                    inline=False
                )
            
            return embed, None
        
        elif result_type == 'list':
            # List query result
            results = result.get('results', [])
            total_count = result.get('total_count', len(results))
            
            embed = create_embed(
                title="📋 Job Listings",
                description=f"**Query:** {query}\n**Total Results:** {total_count}"
            )
            
            for item in results[:Config.MAX_RESULTS_DISPLAY]:
                embed.add_field(
                    name=item.get('name', 'N/A'),
                    value=item.get('value', 'N/A'),
                    inline=item.get('inline', False)
                )
            
            if total_count > len(results):
                embed.set_footer(text=f"Showing {len(results)} of {total_count} results")
            
            return embed
        
        elif result_type == 'stats':
            # Statistics query result
            stats = result.get('stats', {})
            message = result.get('message', 'Statistics')
            
            embed = create_embed(
                title="📈 Statistics",
                description=message
            )
            
            for key, value in stats.items():
                embed.add_field(
                    name=str(key),
                    value=str(value),
                    inline=True
                )
            
            return embed
        
        elif result_type == 'help':
            # Help query result
            message = result.get('message', 'No help available')
            
            embed = create_embed(
                title="❓ Help - JoeBot Query Guide",
                description=message
            )
            
            return embed
        
        
        elif result_type == 'agent_response':
            # Agent mode response (may include chart)
            message_text = result.get('message', 'Query processed')
            charts = result.get('charts', [])
            
            # Use first chart if available
            chart_path = charts[0] if charts else None
            
            # Return plain text for agent responses
            return message_text[:2000], chart_path
        
        else:
            # Unknown result type
            return create_embed(
                title="Results",
                description=result.get('message', 'Query processed')
            ), None


def create_bot(database: SQLJobDatabase) -> JobBoardBot:
    """
    Create and configure the Discord bot.
    
    Args:
        database: Loaded job database
    
    Returns:
        Configured JobBoardBot instance
    """
    bot = JobBoardBot(database)
    return bot
