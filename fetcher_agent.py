"""Fetcher Agent - Deterministic data retrieval tool for Summary Agent.

This agent executes database queries based on instructions from the Summary Agent.
It's implemented as pure Python code, not an LLM.
"""
import logging
from typing import Dict, Any, List, Optional
from database import SQLJobDatabase, JobPosting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FetcherAgent:
    """Execute data retrieval operations as a tool for the Summary Agent."""
    
    def __init__(self, database: SQLJobDatabase):
        """
        Initialize the Fetcher Agent.
        
        Args:
            database: The loaded job database
        """
        self.db = database
        logger.info("FetcherAgent initialized")
    
    def fetch_data(self, filters: Dict[str, Any] = None, fetch_type: str = "count",
                   limit: int = 25, **kwargs) -> Dict[str, Any]:
        """
        Execute data retrieval based on filters and fetch type.
        
        This is called by the Summary Agent as a tool.
        
        Args:
            filters: Dictionary of filters (year, state, institution, etc.)
            fetch_type: Type of fetch - "count", "list", "aggregate", "compare"
            limit: Maximum results for list queries
            **kwargs: Catch-all for hallucinated top-level args
        """
        filters = filters or {}
        
        # Helper: Merge top-level kwargs into filters if they match known filter keys
        # This handles cases where LLM flattens arguments
        known_filters = [
            'year', 'institution', 'country', 'state', 'section', 'department', 
            'keywords', 'jel_classification', 'year_min', 'year_max', 
            'seasonal_start', 'seasonal_end', 'start_year', 'end_year', 
            'aggregate_by', 'compare_by', 'compare_values'
        ]
        
        for k, v in kwargs.items():
            if k in known_filters and k not in filters:
                filters[k] = v
        
        try:
            # Handle flattened args (LLM sometimes passes these effectively)
            if 'aggregate_by' in kwargs:
                filters['aggregate_by'] = kwargs['aggregate_by']
            if 'compare_by' in kwargs:
                filters['compare_by'] = kwargs['compare_by']
            if 'compare_values' in kwargs:
                filters['compare_values'] = kwargs['compare_values']
            
            logger.info(f"Fetching data: type={fetch_type}, filters={filters}")
            
            if fetch_type == "count":
                return self._count_jobs(filters)
            elif fetch_type == "list":
                return self._list_jobs(filters, limit)
            elif fetch_type == "aggregate":
                return self._aggregate_jobs(filters)
            elif fetch_type == "compare":
                return self._compare_jobs(filters)
            else:
                return {"error": f"Unknown fetch_type: {fetch_type}"}
        
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return {"error": str(e)}
    
    def get_last_sql(self) -> Dict[str, str]:
        """Retrieve the last executed SQL query."""
        if hasattr(self.db, 'last_query') and self.db.last_query:
            return {"sql": self.db.last_query}
        return {"sql": "No query executed yet."}

    def _count_jobs(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Count jobs matching filters."""
        jobs = self._filter_jobs(filters)
        
        return {
            "count": len(jobs),
            "filters_applied": filters,
            "sample_size": min(5, len(jobs)),
            "sample_titles": [j.title for j in jobs[:5]]
        }
    
    def _list_jobs(self, filters: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """List job details matching filters."""
        jobs = self._filter_jobs(filters)
        
        job_list = []
        for job in jobs[:limit]:
            location_str = self._format_location(job.locations)
            job_list.append({
                "title": job.title,
                "institution": job.institution,
                "year": job.year,
                "location": location_str,
                "department": job.department or "N/A",
                "section": job.section or "N/A"
            })
        
        return {
            "total_count": len(jobs),
            "returned_count": len(job_list),
            "jobs": job_list,
            "filters_applied": filters
        }
    
    def _aggregate_jobs(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate jobs by specified dimension."""
        jobs = self._filter_jobs(filters)
        
        # Determine aggregation dimension
        agg_by = filters.get('aggregate_by', 'state')
        
        aggregation = {}
        multi_jel_count = 0
        for job in jobs:
            if agg_by == 'state':
                for loc in job.locations:
                    state = loc.get('state', 'Unknown')
                    aggregation[state] = aggregation.get(state, 0) + 1
            elif agg_by == 'institution':
                inst = job.institution or 'Unknown'
                aggregation[inst] = aggregation.get(inst, 0) + 1
            elif agg_by == 'year':
                year = job.year or 'Unknown'
                aggregation[year] = aggregation.get(year, 0) + 1
            elif agg_by == 'country':
                for loc in job.locations:
                    country = loc.get('country', 'Unknown')
                    aggregation[country] = aggregation.get(country, 0) + 1
            
            elif agg_by == 'jel_classification':
                raw_jel = job.jel_classification or 'Unknown'
                # Split multiple classifications (usually newline separated)
                parts = [p.strip() for p in raw_jel.replace('\r', '\n').split('\n') if p.strip()]
                
                # Track multi-classification usage
                if len(parts) > 1:
                    multi_jel_count += 1
                    
                for part in parts:
                    aggregation[part] = aggregation.get(part, 0) + 1
        
        # Sort by count descending
        sorted_agg = dict(sorted(aggregation.items(), key=lambda x: x[1], reverse=True))
        
        # Limit breakdown size to prevent context overflow (e.g. 5000+ JEL codes)
        # Keep top 50 for detail, provide count for "how many" questions
        top_50 = dict(list(sorted_agg.items())[:50])
        
        return {
            "total_count": len(jobs),
            "jobs_with_multiple_codes": multi_jel_count if agg_by == 'jel_classification' else None,
            "aggregated_by": agg_by,
            "unique_value_count": len(sorted_agg),
            "breakdown": top_50,
            "top_10": dict(list(sorted_agg.items())[:10]),
            "filters_applied": filters
        }
    
    def _compare_jobs(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Compare job counts across multiple criteria."""
        compare_dimension = filters.get('compare_by', 'year')
        compare_values = filters.get('compare_values', [])
        
        if not compare_values:
            return {"error": "No compare_values provided"}
        
        results = {}
        for value in compare_values:
            value_filters = filters.copy()
            value_filters[compare_dimension] = value
            value_filters.pop('compare_by', None)
            value_filters.pop('compare_values', None)
            
            jobs = self._filter_jobs(value_filters)
            results[str(value)] = {
                "count": len(jobs),
                "filters": value_filters
            }
        
        return {
            "comparison": results,
            "compare_dimension": compare_dimension,
            "original_filters": filters
        }
    
    def _filter_jobs(self, filters: Dict[str, Any]) -> List[JobPosting]:
        """Filter jobs using direct SQL queries."""
        conditions = ["1=1"]
        params = []
        
        # Extract filters
        year = filters.get('year')
        institution = filters.get('institution')
        country = filters.get('country')
        state = filters.get('state')
        section = filters.get('section')
        department = filters.get('department')
        keywords = filters.get('keywords')
        jel_classification = filters.get('jel_classification')
        
        # Advanced date filters
        year_min = filters.get('year_min') or filters.get('start_year')
        year_max = filters.get('year_max') or filters.get('end_year')
        seasonal_start = filters.get('seasonal_start')  # MM-DD
        seasonal_end = filters.get('seasonal_end')      # MM-DD
        
        if year:
            conditions.append("year = ?")
            params.append(str(year))
        
        if year_min:
            conditions.append("year >= ?")
            params.append(str(year_min))
            
        if year_max:
            conditions.append("year <= ?")
            params.append(str(year_max))
            
        # Seasonal filtering (e.g. "between 10-01 and 12-25 each year")
        if seasonal_start and seasonal_end:
            # Use SQLite strftime to extract MM-DD
            conditions.append("strftime('%m-%d', date_active) BETWEEN ? AND ?")
            params.append(seasonal_start)
            params.append(seasonal_end)
            
        if institution:
            conditions.append("institution LIKE ?")
            params.append(f"%{institution}%")
            
        if country:
            conditions.append("location LIKE ?")
            params.append(f"%{country}%")
            
        if state:
            conditions.append("location LIKE ?")
            params.append(f"%{state}%")
            
        if section:
            conditions.append("section LIKE ?")
            params.append(f"%{section}%")
            
        if department:
            conditions.append("department LIKE ?")
            params.append(f"%{department}%")
            
        if jel_classification:
            conditions.append("jel_classification LIKE ?")
            params.append(f"%{jel_classification}%")
            
        if keywords:
            # Search in keywords, title, or description
            conditions.append("(keywords LIKE ? OR title LIKE ? OR description LIKE ?)")
            term = f"%{keywords}%"
            params.extend([term, term, term])
            
        sql = f"SELECT * FROM jobs WHERE {' AND '.join(conditions)}"
        
        # Execute via DB (which captures the query)
        return self.db.query_jobs(sql, tuple(params))
    
    def _format_location(self, locations: List[Dict[str, str]]) -> str:
        """Format location information as a string."""
        if not locations:
            return "N/A"
        
        loc_strs = []
        for loc in locations[:2]:
            parts = [loc.get('city'), loc.get('state'), loc.get('country')]
            parts = [p for p in parts if p]
            if parts:
                loc_strs.append(', '.join(parts))
        
        result = ' | '.join(loc_strs)
        if len(locations) > 2:
            result += f' (+{len(locations) - 2} more)'
        
        return result or "N/A"
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Return OpenAI tool definition for this agent.
        Used by Summary Agent to call this as a tool.
        """
        return [
            {
                "type": "function",
            "function": {
                "name": "fetch_job_data",
                "description": "Fetch job posting data from the database with specified filters and aggregation type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filters": {
                            "type": "object",
                            "description": "Filters to apply",
                            "properties": {
                                "year": {"type": "string", "description": "Specific Year (e.g., '2024')"},
                                "year_min": {"type": "integer", "description": "Start Year (inclusive, e.g. 2018)"},
                                "year_max": {"type": "integer", "description": "End Year (inclusive)"},
                                "seasonal_start": {"type": "string", "description": "Start date for recurring seasonal range (MM-DD, e.g. '10-01')"},
                                "seasonal_end": {"type": "string", "description": "End date for recurring seasonal range (MM-DD, e.g. '12-25')"},
                                "state": {"type": "string", "description": "US state (e.g., 'massachusetts')"},
                                "institution": {"type": "string", "description": "Institution name"},
                                "country": {"type": "string", "description": "Country name"},
                                "section": {"type": "string", "description": "Job section/type"},
                                "department": {"type": "string", "description": "Department name"},
                                "jel_classification": {"type": "string", "description": "JEL Classification code (e.g. 'C1', 'L2')"},
                                "keywords": {"type": "string", "description": "Search keywords"},
                                "aggregate_by": {"type": "string", "enum": ["state", "institution", "year", "country", "jel_classification"]},
                                "compare_by": {"type": "string", "description": "Dimension to compare (e.g. 'year' to see trends over time)"},
                                "compare_values": {"type": "array", "items": {"type": "string"}}
                            }
                        },
                        "fetch_type": {
                            "type": "string",
                            "enum": ["count", "list", "aggregate", "compare"],
                            "description": "Type of data retrieval. Use 'aggregate' with aggregate_by='year' for time trends."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results for list queries (default 25)"
                        }
                    },
                    "required": ["filters", "fetch_type"]
                }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_last_sql",
                    "description": "Get the SQL query used for the most recent data fetch. Use this when the user asks to see the SQL.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
