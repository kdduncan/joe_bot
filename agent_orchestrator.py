"""Agent Orchestrator - Coordinates Summary Agent, Fetcher Agent, and Visualization Agent.

This orchestrator manages the multi-agent loop for intelligent query processing.
"""
import logging
from typing import Dict, Any
from summary_agent import SummaryAgent
from fetcher_agent import FetcherAgent
from visualization_agent import VisualizationAgent
from database import SQLJobDatabase

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
        self.summary_agent = SummaryAgent()
        self.fetcher_agent = FetcherAgent(database)
        self.visualization_agent = VisualizationAgent()
        self.enabled = self.summary_agent.enabled
        
        if self.enabled:
            logger.info("AgentOrchestrator initialized (agent mode enabled with visualization)")
        else:
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
            # fetcher_agent returns a list (may contain multiple tools)
            # visualization_agent returns a single dict (for now)
            fetcher_tools = self.fetcher_agent.get_tool_definition()
            viz_tool = self.visualization_agent.get_tool_definition()
            
            tools = []
            if isinstance(fetcher_tools, list):
                tools.extend(fetcher_tools)
            else:
                tools.append(fetcher_tools)
                
            tools.append(viz_tool)
            
            # Create callbacks for tools
            tool_callbacks = {
                'fetch_job_data': self.fetcher_agent.fetch_data,
                'create_chart': self.visualization_agent.create_chart,
                'get_last_sql': self.fetcher_agent.get_last_sql
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
