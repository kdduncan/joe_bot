"""Utility functions for the Discord Job Board Bot."""
from datetime import datetime
from typing import List, Dict, Any
import discord
from config import Config


def parse_date(date_str: str) -> datetime:
    """
    Parse a date string from the XML format.
    
    Args:
        date_str: Date string in format 'YYYY-MM-DD HH:MM:SS'
    
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str or not date_str.strip():
        return None
    
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None


def format_date(dt: datetime) -> str:
    """Format a datetime object as a readable string."""
    if not dt:
        return "N/A"
    return dt.strftime('%B %d, %Y')


def truncate_text(text: str, max_length: int = 1024) -> str:
    """
    Truncate text to a maximum length, adding ellipsis if needed.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including ellipsis
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def create_embed(title: str, description: str = None, color: int = None) -> discord.Embed:
    """
    Create a Discord embed with consistent styling.
    
    Args:
        title: Embed title
        description: Embed description
        color: Embed color (defaults to Config.EMBED_COLOR)
    
    Returns:
        Discord Embed object
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or Config.EMBED_COLOR,
        timestamp=datetime.utcnow()
    )
    return embed


def create_results_embed(query: str, results: List[Dict[str, Any]], total_count: int = None) -> discord.Embed:
    """
    Create an embed to display query results.
    
    Args:
        query: The original query
        results: List of result dictionaries
        total_count: Total count if results are paginated
    
    Returns:
        Discord Embed object
    """
    if total_count is None:
        total_count = len(results)
    
    embed = create_embed(
        title=f"Query Results",
        description=f"**Query:** {query}\n**Results:** {total_count}"
    )
    
    # Add results as fields (limited to avoid embed size limits)
    display_count = min(len(results), Config.MAX_RESULTS_DISPLAY)
    
    for i, result in enumerate(results[:display_count]):
        name = result.get('name', f'Result {i+1}')
        value = result.get('value', 'No data')
        embed.add_field(
            name=truncate_text(name, 256),
            value=truncate_text(str(value), 1024),
            inline=result.get('inline', False)
        )
    
    if total_count > display_count:
        embed.set_footer(text=f"Showing {display_count} of {total_count} results")
    
    return embed


def create_error_embed(error_message: str) -> discord.Embed:
    """
    Create an embed for error messages.
    
    Args:
        error_message: The error message to display
    
    Returns:
        Discord Embed object with red color
    """
    embed = discord.Embed(
        title="❌ Error",
        description=error_message,
        color=0xED4245,  # Discord red
        timestamp=datetime.utcnow()
    )
    return embed


def create_stats_embed(title: str, stats: Dict[str, Any]) -> discord.Embed:
    """
    Create an embed for displaying statistics.
    
    Args:
        title: Title for the statistics
        stats: Dictionary of statistic name -> value pairs
    
    Returns:
        Discord Embed object
    """
    embed = create_embed(title=title)
    
    for key, value in stats.items():
        embed.add_field(
            name=key,
            value=str(value),
            inline=True
        )
    
    return embed
