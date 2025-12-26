"""Query engine for natural language processing of job posting queries.

SECURITY: Safe from prompt injection attacks.
- User input is ONLY used for pattern matching (regex, string search)
- No code execution (no eval, exec, or compile)
- No system commands or file operations
- Queries only filter existing in-memory data
- Agent mode uses LLM for intelligent interpretation but all data access is read-only
"""
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter
from database import SQLJobDatabase, JobPosting
from config import Config

# Try to import Agent Orchestrator
try:
    from agent_orchestrator import AgentOrchestrator
    AGENT_MODE_AVAILABLE = True
except ImportError:
    AGENT_MODE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Agent mode not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryEngine:
    """Process natural language queries against the job database."""
    
    def __init__(self, database: SQLJobDatabase):
        """
        Initialize the query engine.
        
        Args:
            database: The loaded job database
        """
        self.db = database
        self.agent_orchestrator = None
        
        # Initialize Agent Orchestrator if enabled
        if Config.USE_AGENT_MODE and AGENT_MODE_AVAILABLE and Config.OPENROUTER_API_KEY:
            try:
                self.agent_orchestrator = AgentOrchestrator(database)
                logger.info(f"QueryEngine initialized (Agent mode: {'enabled' if self.agent_orchestrator.enabled else 'disabled'})")
            except Exception as e:
                logger.warning(f"Failed to initialize Agent mode: {e}")
        
        if not self.agent_orchestrator:
            logger.info("QueryEngine initialized (pattern matching only)")
    
    
    def process_query(self, query: str, context_id: str = None) -> Dict[str, Any]:
        """
        Process a natural language query.
        
        Args:
            query: The question text
            context_id: Optional context identifier for history
            
        Returns:
            Dictionary with results or error
        """
        query_lower = query.lower().strip()
        
        try:
            # 1. Try Agent Mode first (if enabled)
            if Config.USE_AGENT_MODE and self.agent_orchestrator and self.agent_orchestrator.enabled:
                try:
                    # Basic check for non-query commands (like help) - let pattern matcher handle those?
                    # Actually, help is better handled by pattern matcher
                    if query_lower == 'help':
                        return self._help_message()
                    
                    # Use Agent
                    logger.info("Processing with Agent Orchestrator")
                    result = self.agent_orchestrator.process_query(query, context_id=context_id)
                    if result.get('type') != 'error':
                        return result
                    else:
                        logger.warning(f"Agent mode failed: {result.get('message')}, falling back to pattern matching")
                except Exception as e:
                    logger.error(f"Agent mode failed, falling back to pattern matching: {e}")
            
            # Fallback to pattern matching (always works)
            logger.info("Processing with pattern matching")
            return self._pattern_match_query(query_lower)
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'type': 'error',
                'message': f'Error processing query: {str(e)}'
            }
    
    def _pattern_match_query(self, query: str) -> Dict[str, Any]:
        """Original pattern matching logic (fallback)."""
        # Show SQL query (Check this first to avoid 'show' matching list queries)
        if any(word in query for word in ['show sql', 'debug sql', 'last query', 'show query']):
            return self._handle_sql_query()

        # Count queries
        if any(word in query for word in ['how many', 'count', 'number of']):
            return self._handle_count_query(query)
        
        # List queries
        elif any(word in query for word in ['list', 'show', 'find', 'get']):
            return self._handle_list_query(query)
        
        # Statistics queries
        elif any(word in query for word in ['stats', 'statistics', 'breakdown', 'by country', 'by institution', 'by year']):
            return self._handle_stats_query(query)
        
        # Help query
        elif any(word in query for word in ['help', 'what can', 'how to']):
            return self._handle_help_query()
        
        
        else:
            # Default: try to parse as a count query
            return self._handle_count_query(query)
    
    def _handle_count_query(self, query: str) -> Dict[str, Any]:
        """Handle count/how many queries."""
        # Extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        year = year_match.group(0) if year_match else None
        
        # Extract institution
        institution = None
        for inst in self.db.get_institutions():
            if inst in query:
                institution = inst
                break
        
        # Extract country
        country = None
        for ctry in self.db.get_countries():
            if ctry in query:
                country = ctry
                break
        
        # Extract state
        state = None
        for st in self.db.get_states():
            if st in query:
                state = st
                break
        
        # Extract job type/section
        section_keywords = {
            'full-time': 'full-time',
            'tenure': 'tenure',
            'visiting': 'visiting',
            'temporary': 'temporary',
            'postdoc': 'postdoc',
            'nonacademic': 'nonacademic'
        }
        section = None
        for keyword, section_type in section_keywords.items():
            if keyword in query:
                section = section_type
                break
        
        # Get matching jobs
        jobs = self._filter_jobs(year=year, institution=institution, country=country, state=state, section=section)
        count = len(jobs)
        
        # Build description
        filters = []
        if year:
            filters.append(f"year {year}")
        if institution:
            filters.append(f"institution '{institution}'")
        if country:
            filters.append(f"country '{country}'")
        if state:
            filters.append(f"state '{state}'")
        if section:
            filters.append(f"type '{section}'")
        
        filter_desc = " and ".join(filters) if filters else "total"
        
        return {
            'type': 'count',
            'count': count,
            'message': f"Found **{count}** job posting(s) for {filter_desc}",
            'filters': {
                'year': year,
                'institution': institution,
                'country': country,
                'state': state,
                'section': section
            }
        }
    
    def _handle_list_query(self, query: str) -> Dict[str, Any]:
        """Handle list/show queries."""
        # Similar filtering as count but return job details
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        year = year_match.group(0) if year_match else None
        
        institution = None
        for inst in self.db.get_institutions():
            if inst in query:
                institution = inst
                break
        
        country = None
        for ctry in self.db.get_countries():
            if ctry in query:
                country = ctry
                break
        
        state = None
        for st in self.db.get_states():
            if st in query:
                state = st
                break
        
        jobs = self._filter_jobs(year=year, institution=institution, country=country, state=state)
        
        # Limit results
        max_display = 25
        jobs_to_show = jobs[:max_display]
        
        results = []
        for job in jobs_to_show:
            location_str = self._format_location(job.locations)
            results.append({
                'name': f"{job.title} - {job.institution}",
                'value': f"Year: {job.year} | Location: {location_str}",
                'inline': False
            })
        
        return {
            'type': 'list',
            'results': results,
            'total_count': len(jobs),
            'message': f"Found {len(jobs)} job posting(s)"
        }
    
    def _handle_stats_query(self, query: str) -> Dict[str, Any]:
        """Handle statistics/breakdown queries."""
        # Determine what kind of breakdown
        if 'by country' in query or 'countries' in query:
            return self._stats_by_country()
        elif 'by institution' in query or 'institutions' in query:
            return self._stats_by_institution()
        elif 'by year' in query or 'years' in query:
            return self._stats_by_year()
        elif 'by type' in query or 'by section' in query:
            return self._stats_by_section()
        else:
            # Default: overall statistics
            return self._overall_stats()
    
    def _stats_by_year(self) -> Dict[str, Any]:
        """Get statistics broken down by year."""
        year_counts = {}
        for year in self.db.get_years():
            year_counts[year] = len(self.db.get_by_year(year))
        
        stats = {f"Year {year}": count for year, count in sorted(year_counts.items())}
        
        return {
            'type': 'stats',
            'stats': stats,
            'message': f"Job postings by year"
        }
    
    def _stats_by_country(self) -> Dict[str, Any]:
        """Get statistics broken down by country."""
        country_counts = {}
        for country in self.db.get_countries():
            country_counts[country] = len(self.db.get_by_country(country))
        
        # Top 15 countries
        top_countries = dict(sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:15])
        
        return {
            'type': 'stats',
            'stats': top_countries,
            'message': f"Top job postings by country (top 15)"
        }
    
    def _stats_by_institution(self) -> Dict[str, Any]:
        """Get statistics broken down by institution."""
        institution_counts = {}
        for inst in self.db.get_institutions():
            institution_counts[inst] = len(self.db.get_by_institution(inst))
        
        # Top 15 institutions
        top_institutions = dict(sorted(institution_counts.items(), key=lambda x: x[1], reverse=True)[:15])
        
        return {
            'type': 'stats',
            'stats': top_institutions,
            'message': f"Top job postings by institution (top 15)"
        }
    
    def _stats_by_section(self) -> Dict[str, Any]:
        """Get statistics broken down by job section/type."""
        section_counts = Counter()
        for job in self.db.get_all_jobs():
            if job.section:
                section_counts[job.section] += 1
        
        stats = dict(section_counts.most_common(15))
        
        return {
            'type': 'stats',
            'stats': stats,
            'message': f"Job postings by type/section"
        }
    
    def _overall_stats(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        all_jobs = self.db.get_all_jobs()
        
        stats = {
            'Total Jobs': len(all_jobs),
            'Years': len(self.db.get_years()),
            'Institutions': len(self.db.get_institutions()),
            'Countries': len(self.db.get_countries())
        }
        
        return {
            'type': 'stats',
            'stats': stats,
            'message': "Overall Database Statistics"
        }

    def _help_message(self) -> Dict[str, Any]:
        """Return help message."""
        help_text = """
JoeBot Query Guide:

1. Count Queries:
   "how many jobs in 2024"
   "count jobs at Harvard"

2. List Queries:
   "list jobs in Boston"
   "show jobs at Yale"

3. Statistics:
   "stats by year"
   "stats by country"
"""
        
        return {
            'type': 'help',
            'message': help_text
        }
    
    def _handle_sql_query(self) -> Dict[str, Any]:
        """Return the last executed SQL query."""
        if hasattr(self.db, 'last_query') and self.db.last_query:
            sql = self.db.last_query
            return {
                'type': 'info',
                'message': f"Last executed SQL query:\n```sql\n{sql}\n```"
            }
        else:
            return {
                'type': 'info',
                'message': "No SQL query has been executed yet."
            }
    
    def _filter_jobs(self, query: str = None, year: str = None, institution: str = None, 
                     country: str = None, state: str = None, section: str = None, 
                     department: str = None, keywords: str = None) -> List[JobPosting]:
        """
        Filter jobs based on criteria using SQL.
        Can accept a query string (to extract filters) or direct filter arguments.
        """
        conditions = ["1=1"]
        params = []
        
        # If query string provided, try to extract missing fields
        if query:
            if not year: year = self._extract_year_from_query(query)
            if not institution: institution = self._extract_institution_from_query(query)
            if not country: country = self._extract_country_from_query(query)
            if not state: state = self._extract_state_from_query(query)
        
        # 1. Apply Year
        if year:
            conditions.append("year = ?")
            params.append(year)

            
            
        # 2. Apply Country
        if country:
            conditions.append("location LIKE ?")
            params.append(f"%{country}%")
            
        # 3. Apply Institution
        if institution:
            conditions.append("institution LIKE ?")
            params.append(f"%{institution}%")
            
        # 4. Apply State
        if state:
            conditions.append("location LIKE ?")
            params.append(f"%{state}%")

        # 5. Apply Section/Type
        if section:
            conditions.append("section LIKE ?")
            params.append(f"%{section}%")

        # 6. Apply Department
        if department:
            conditions.append("department LIKE ?")
            params.append(f"%{department}%")

        # 7. Apply Keywords
        if keywords:
            conditions.append("(keywords LIKE ? OR description LIKE ?)")
            term = f"%{keywords}%"
            params.extend([term, term])
            
        # Construct SQL
        sql = f"SELECT * FROM jobs WHERE {' AND '.join(conditions)}"
        
        # Execute query
        return self.db.query_jobs(sql, tuple(params))
    
    def _format_location(self, locations: List[Dict[str, str]]) -> str:
        """Format location information as a string."""
        if not locations:
            return "N/A"
        
        loc_strs = []
        for loc in locations[:2]:  # Show max 2 locations
            parts = [loc.get('city'), loc.get('state'), loc.get('country')]
            parts = [p for p in parts if p]
            if parts:
                loc_strs.append(', '.join(parts))
        
        result = ' | '.join(loc_strs)
        if len(locations) > 2:
            result += f' (+{len(locations) - 2} more)'
        
        return result or "N/A"
