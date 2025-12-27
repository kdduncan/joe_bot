"""Agent Orchestrator - Coordinates Summary Agent, Fetcher Agent, and Visualization Agent.

This orchestrator manages the multi-agent loop for intelligent query processing.
"""
import logging
from typing import Dict, Any
from summary_agent import SummaryAgent
from fetcher_agent import FetcherAgent
from visualization_agent import VisualizationAgent
from database import SQLJobDatabase
from config import Config
from sql_agent import SQLAgent # New Pete!

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinates the multi-agent query processing loop."""
    
    def __init__(self, database: SQLJobDatabase):
        """
        Initialize the orchestrator with agents.
        
        Args:
            database: The loaded job database
        """
        self.database = database
        self.db = database
        self.client = None
        self.enabled = Config.USE_AGENT_MODE and bool(Config.OPENROUTER_API_KEY)
        
        if self.enabled:
            # Initialize Agents
            self.fetcher_agent = FetcherAgent(database) # Keeping for legacy/backup if needed? Or remove?
            # Actually, let's keep fetcher as "Legacy Pete" if we want, but user wants True Pete.
            # We will use SQLAgent as the primary data tool.
            self.sql_agent = SQLAgent(database)
            self.visualization_agent = VisualizationAgent()
            self.summary_agent = SummaryAgent() # Fixed: No args in init
            
            logger.info("AgentOrchestrator initialized (agent mode enabled with visualization)")
        else:
            # Initialize agents even if disabled, but they won't be used.
            # This prevents AttributeError if trying to access them later.
            self.fetcher_agent = FetcherAgent(database)
            self.sql_agent = SQLAgent(database)
            self.visualization_agent = VisualizationAgent()
            self.summary_agent = SummaryAgent()
            logger.info("AgentOrchestrator initialized (agent mode disabled - will use fallback)")
    
    
    def process_query(self, user_query: str, context_id: str = None) -> Dict[str, Any]:
        """
        Process a query using the multi-agent loop.
        
        Args:
            user_query: The user's natural language query
            context_id: Optional context identifier (e.g., channel ID) for conversation history
        
        Returns:
            Dictionary with response type and content
        """
        if not self.enabled:
            return {
                'type': 'error',
                'message': 'Agent mode is disabled. Please configure OpenRouter API key.'
            }
        
        try:
            # Get tool definitions
            # Pete's tools (now a list):
            pete_tools = self.sql_agent.get_tool_definition()
            viz_tool = self.visualization_agent.get_tool_definition()
            
            tools = []
            if isinstance(pete_tools, list):
                tools.extend(pete_tools)
            else:
                tools.append(pete_tools)
                
            tools.append(viz_tool)
            
            # Create callbacks for tools
            tool_callbacks = {
                'ask_pete': self.sql_agent.ask_pete,
                'get_last_sql': self.sql_agent.get_last_sql,
                'create_chart': self.visualization_agent.create_chart
            }
            
            # Process with Summary Agent using both tools
            agent_result = self.summary_agent.process_query_with_tools(
                user_query=user_query,
                tools=tools,
                tool_callbacks=tool_callbacks,
                conversation_id=context_id
            )
            
            # Extract content and charts
            if isinstance(agent_result, dict):
                summary = agent_result.get('content', '')
                charts = agent_result.get('charts', [])
            else:
                summary = str(agent_result)
                charts = []
            
            return {
                'type': 'agent_response',
                'message': summary,
                'charts': charts,
                'agent_mode': True
            }
        
        except Exception as e:
            logger.error(f"Error in agent orchestration: {e}")
            return {
                'type': 'error',
                'message': f"Agent processing error: {str(e)}"
            }
