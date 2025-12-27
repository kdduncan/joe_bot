"""
SQL Agent module (Pete).
Uses LLM to generate SQL queries for the job database.
"""
import logging
import json
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI
from config import Config
from database import SQLJobDatabase

logger = logging.getLogger(__name__)

class SQLAgent:
    """
    "Pete" the SQL Agent.
    Translates natural language questions into SQL queries for jobs.db.
    """
    def __init__(self, database: SQLJobDatabase):
        self.db = database
        self.model = Config.AGENT_MODEL or "openai/gpt-4o-mini"
        self.enabled = Config.USE_AGENT_MODE and bool(Config.OPENROUTER_API_KEY)
        
        if self.enabled:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=Config.OPENROUTER_API_KEY,
            )
            logger.info("SQLAgent (Pete) initialized with OpenRouter")
        else:
            self.client = None
            logger.warning("SQLAgent disabled (no API key)")

    def get_tool_definition(self) -> List[Dict[str, Any]]:
        """Return the tool definitions for John to call."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "ask_pete",
                    "description": "Ask Pete (the SQL Expert) to query the database. Use this for ANY data request.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The natural language question to ask Pete (e.g., 'How many jobs in Iowa in 2024?')"
                            }
                        },
                        "required": ["question"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_last_sql",
                    "description": "Get the SQL query used for the last request (to answer user questions like 'What was the query?').Params: None.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
        return tools

    def get_last_sql(self) -> Dict[str, Any]:
        """Retrieve the last executed SQL query."""
        if self.db.last_query:
            return {"sql": self.db.last_query}
        return {"sql": "No query has been executed yet."}

    def ask_pete(self, question: str = None, **kwargs) -> Dict[str, Any]:
        """
        Process a natural language question -> Generate SQL -> Execute -> Return Data.
        """
        if not self.enabled:
            return {"error": "SQL Agent is disabled."}

        # Robust argument handling
        if not question:
            # Check aliases/kwargs
            question = kwargs.get('query') or kwargs.get('content') or kwargs.get('prompt')
        
        if not question:
            return {
                "error": "Missing 'question' argument. Please call ask_pete with a specific question string (e.g., {'question': 'rows in jobs'})."
            }

        logger.info(f"Pete received question: {question}")
        
        # 1. Get Schema
        schema = self.db.get_schema_string()
        
        # 2. Generate SQL via LLM
        system_prompt = f"""You are Pete, an expert SQL Data Analyst.
Your goal is to write a SQLite query to answer the user's question about the job market.

DATABASE SCHEMA:
{schema}

IMPORTANT RULES:
1. ONLY write the SQL query. Do not wrap it in markdown block if possible, or I will strip it.
2. The table name is `jobs`.
3. Use `LIKE` for text matching (case-insensitive in SQLite usually, but use matching wildcards).
4. `jel_classification` contains codes like 'C1', 'L2'. Use `LIKE '%C1%'` to search.
5. Dates are text (YYYY-MM-DD) or `year` (int).
6. **SAFETY**: Read-only. SELECT statements only. NO DROP, DELETE, INSERT.
7. Return only the SQL.

EXAMPLE:
Q: Count jobs in 2024?
A: SELECT count(*) FROM jobs WHERE year = 2024;
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Question: {question}"}
                ],
                temperature=0.1 # Low temperature for code
            )
            
            sql_response = response.choices[0].message.content.strip()
            
            # Clean SQL (remove markdown blocks if present)
            clean_sql = self._clean_sql_block(sql_response)
            
            logger.info(f"Pete generated SQL: {clean_sql}")
            
            # 3. Validation
            if not clean_sql.upper().startswith("SELECT"):
                 # Fallback/Safety check
                 return {"error": "Pete refused to write a SELECT query.", "raw_response": sql_response}
                 
            # 4. Execute
            # Use execute_raw_query (we need to make sure execute_raw_query exists and accepts raw strings)
            # database.py has execute_raw_query(query, params)
            # Pete generates full SQL with literals (usually). 
            # Ideally we parameterize, but generating parameterized SQL + tuple from LLM is hard.
            # We will rely on read-only enforcement and internal safety (DB is local file).
            # SECURITY NOTE: This executes LLM-generated SQL. 
            # Since user intent IS to solve arbitrary queries, this is the feature.
            # We catch errors.
            
            results = self.db.execute_raw_query(clean_sql)
            
            # 5. Return result structure
            # Return dict with SQL (for John/User to see) and Data.
            return {
                "sql": clean_sql,
                "data": results[:100], # Limit rows to prevent context overflow in John
                "row_count": len(results),
                "note": "Rows limited to 100" if len(results) >= 100 else None
            }
            
        except Exception as e:
            logger.error(f"Pete failed: {e}")
            return {"error": str(e)}

    def _clean_sql_block(self, text: str) -> str:
        """Remove markdown code blocks ```sql ... ```"""
        match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
        return text.strip()
