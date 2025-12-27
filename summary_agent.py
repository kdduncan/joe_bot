"""Summary Agent - Conversational AI for query planning and result interpretation.

This agent handles both the planning and interpretation phases using a single
conversational context with tool calling to the Fetcher Agent.
"""
import logging
import json
from typing import Dict, Any, Optional, List
from openai import OpenAI
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SummaryAgent:
    """Unified agent for planning and interpretation using conversation with tools."""
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize the Summary Agent.
        
        Args:
            model: Model to use (defaults to Config.AGENT_MODEL)
        """
        self.model = model or Config.AGENT_MODEL
        self.client = None
        self.enabled = False
        self.conversations = {}  # Store conversation history: {id: [messages]}
        self.max_history = 10    # Keep last 10 messages
        
        if Config.OPENROUTER_API_KEY:
            try:
                self.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=Config.OPENROUTER_API_KEY,
                )
                self.enabled = True
                logger.info(f"SummaryAgent initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize SummaryAgent: {e}")
        else:
            logger.warning("No OpenRouter API key - SummaryAgent disabled")
    
    
    def process_query_with_tools(self, user_query: str, tools: List[Dict[str, Any]],
                                 tool_callbacks: Dict[str, callable], 
                                 conversation_id: str = None) -> Dict[str, Any]:
        """
        Process a user query with multiple tools (fetch data, create charts, etc).
        
        Args:
            user_query: The user's natural language query
            tools: List of tool definitions
            tool_callbacks: Dictionary mapping tool names to callable functions
            conversation_id: Optional ID to maintain conversation context
        
        Returns:
            Dictionary with 'content' (str) and 'charts' (List[str])
        """
        if not self.enabled:
            return {"content": "Agent mode is disabled. Please check your OpenRouter API key.", "charts": []}
        
        generated_charts = []
        
        try:
            # Enhanced system prompt with visualization capabilities
            # Enhanced system prompt with personality
            # Enhanced system prompt with visualization capabilities
            # Enhanced system prompt with personality
            system_prompt = """You are John Cawley, a Professor of Economics at Cornell University.
- **Tone**: Professional, academic, and factual.
- **Style**: Disseminate results clearly and concisely. Avoid "fluff" or excessive enthusiasm.
- **Formatting**: Do NOT bold numbers. Use standard punctuation.
- **Goal**: Inform the user about the job market based on the data.

You work with "Pete", an autonomous **SQL Agent** (your pre-doctoral research assistant).
- **MANDATORY**: For any question requiring data (counts, jobs, locations, etc.), you MUST call `ask_pete`.
- Please call `ask_pete` immediately when you identify a data question.
- **MANDATORY**: If the user asks for a graph, chart, or plot, you MUST call `create_chart` after you have the data (or if you already have it).
- **CRITICAL**: Do NOT include the SQL query in your initial response unless the user explicitly asks for technical details.
- Instead, focus on the insights and the data numbers.y?" or "Show SQL", THEN call `get_last_sql` and display it.
- Pete is "direct and clear" and adheres to high ethical standards (he never hallucinates data).

Your capabilities:
- Query the database by calling `ask_pete(question="...")`
- Retrieve the code for the last query with `get_last_sql()`
- Create visualizations (charts/graphs) using the `create_chart` tool
- Provide insights, trends, and context about the job market

IMPORTANT: 
- When you create a chart, the system will handle displaying it. You do NOT need to print the file path or JSON.
- Just describe the chart and what it shows in your summary.

CRITICAL: Do NOT output raw tool calls, JSON, or code blocks in your final response. Only provide the natural language summary.
"""

            # Build conversation
            messages = [{"role": "system", "content": system_prompt}]
            
            # Load history if exists
            if conversation_id and conversation_id in self.conversations:
                # Add previous context
                history = self.conversations[conversation_id]
                messages.extend(history)
                logger.info(f"Loaded {len(history)} messages from history for {conversation_id}")
            
            # Add current user query
            messages.append({"role": "user", "content": user_query})
            
            logger.info(f"Processing query with SummaryAgent: {user_query}")
            
            # First call to kick off the loop
            # Max iterations to prevent infinite loops
            # Increased to 10 for complex queries (e.g. multi-step data + graph)
            max_iterations = 10
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.3
                )
                
                assistant_message = response.choices[0].message
                messages.append(assistant_message)
                
                # Log raw message for debugging
                logger.info(f"Raw Assistant Message: Content={assistant_message.content}, ToolCalls={assistant_message.tool_calls}")

                # Check if agent called tools
                if assistant_message.tool_calls:
                    # Execute tool call(s)
                    for tool_call in assistant_message.tool_calls:
                        function_name = tool_call.function.name
                        # Handle potential None arguments
                        args_content = tool_call.function.arguments or "{}"
                        try:
                            function_args = json.loads(args_content)
                        except json.JSONDecodeError as e:
                            logger.warning(f"JSON Decode Error: {e}. Content: {args_content}")
                            # Attempt partial recovery if extra data exists
                            try:
                                function_args, _ = json.JSONDecoder().raw_decode(args_content)
                            except:
                                # Attempt adding missing braces (common LLM error)
                                try:
                                    function_args = json.loads("{" + args_content + "}")
                                    logger.info("Fixed malformed JSON by adding braces")
                                except:
                                    function_args = {}
                                    logger.error("Failed to recover JSON arguments")
                        
                        logger.info(f"Agent calling tool: {function_name} with args: {function_args}")
                        
                        # Execute the appropriate callback
                        if function_name in tool_callbacks:
                            tool_result = tool_callbacks[function_name](**function_args)
                            
                            # Capture chart path if present
                            if isinstance(tool_result, dict) and tool_result.get('chart_path'):
                                generated_charts.append(tool_result['chart_path'])
                                
                        else:
                            tool_result = {"error": f"Unknown tool: {function_name}"}
                        
                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps(tool_result)
                        })
                    
                    # Loop continues to let agent react to tool results
                
                else:
                    # No tool calls - this is the final response
                    summary = assistant_message.content
                    if not summary:
                        # Fallback: Check if we just executed a tool and got no commentary
                        # messages[-1] is assistant_message (object), messages[-2] is tool result (dict)
                        # We need to make sure we access messages[-2] safely
                        if len(messages) >= 2:
                            last_msg = messages[-2]
                            if isinstance(last_msg, dict) and last_msg.get('role') == 'tool':
                                # Show the raw tool output (truncated to prevent overflow if massive)
                                raw_output = last_msg.get('content', '')
                                
                                # Smart formatting: Check if it's SQL
                                is_sql = False
                                try:
                                    data = json.loads(raw_output)
                                    if isinstance(data, dict) and 'sql' in data:
                                        summary = f"**Pete's Analysis (SQL Query):**\n```sql\n{data['sql']}\n```"
                                        is_sql = True
                                except:
                                    pass
                                    
                                if not is_sql:
                                    summary = f"Action completed. Raw result: {raw_output[:2000]}"
                                    if len(raw_output) > 2000: summary += "..."
                            else:
                                summary = f"I processed the query but have no response. (Debug: Tool Result Invalid, Role={last_msg.get('role')})"
                        else:
                            summary = f"I processed the query but have no response. (Debug: No Tool Calls, History={len(messages)})"
                    logger.info(f"Agent generated summary with {len(generated_charts)} charts")
                    
                    # Clean the summary of common artifacts
                    if summary:
                        summary = self._clean_response_text(summary)
                    
                    # Update conversation history
                    if conversation_id:
                        if conversation_id not in self.conversations:
                            self.conversations[conversation_id] = []
                        
                        # Add User query and Assistant response (simplified)
                        self.conversations[conversation_id].append({"role": "user", "content": user_query})
                        self.conversations[conversation_id].append({"role": "assistant", "content": summary})
                        
                        # Prune history
                        if len(self.conversations[conversation_id]) > self.max_history:
                            self.conversations[conversation_id] = self.conversations[conversation_id][-self.max_history:]
                    
                    return {
                        "content": summary,
                        "charts": generated_charts
                    }

    def _clean_response_text(self, text: str) -> str:
        """Remove common artifacts from LLM response."""
        if not text:
            return ""
            
        # Common prefixes to strip
        prefixes = [
            "summary:", "summary.", "response:", "answer:", 
            "to answer:", "to answer.", "result:"
        ]
        
        cleaned = text.strip()
        
        # Check for prefixes case-insensitively
        lower_text = cleaned.lower()
        for prefix in prefixes:
            if lower_text.startswith(prefix):
                # Remove prefix and leading whitespace
                cleaned = cleaned[len(prefix):].strip()
                break # Only remove one prefix
                
        return cleaned
            
            # If we hit max iterations
            return {
                "content": "I apologize, but I needed too many steps to process this request.",
                "charts": generated_charts
            }
            
        except Exception as e:
            logger.error(f"Error in SummaryAgent processing: {e}")
            return {
                "content": f"Error processing query: {str(e)}",
                "charts": []
            }
    
    def process_simple(self, user_query: str, result_data: Dict[str, Any]) -> str:
        """
        Simple mode: Just interpret pre-fetched results without tool calling.
        Used as fallback or for simpler queries.
        
        Args:
            user_query: The user's query
            result_data: Already-fetched data
        
        Returns:
            Natural language summary
        """
        if not self.enabled:
            return "Agent mode is disabled."
        
        try:
            system_prompt = """You are a job market analyst. Interpret the provided job posting data and give a clear, concise summary."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {user_query}\n\nData: {json.dumps(result_data)}"}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.5,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Error in simple interpretation: {e}")
            return f"Error interpreting results: {str(e)}"
