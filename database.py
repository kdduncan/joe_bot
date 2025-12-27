import sqlite3
import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class JobPosting:
    """Represents a single job posting."""
    id: str
    title: str
    institution: str
    department: str
    division: str
    section: str
    location: str
    description: str
    salary_range: str
    keywords: str
    deadline: str
    date_active: str
    year: int
    source_file: str
    jel_classification: str = ""
    
    @property
    def locations(self) -> List[Dict[str, str]]:
        """Backwards compatibility for location list."""
        # Simple parsing for compatibility
        return [{'country': self.location, 'city': ''}]

class SQLJobDatabase:
    """SQLite-based job database."""
    
    def __init__(self, db_path: str = 'jobs.db'):
        """Initialize connection."""
        self.db_path = db_path
        self.last_query = None  # Store last executed query
        self._ensure_db_exists()
        
    def _ensure_db_exists(self):
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}. Run migrate_data.py first.")
            
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_jobs(self) -> List[JobPosting]:
        """Get all jobs (limit to recent/reasonable number if needed)."""
        # For compatibility, returns all, but in practice should filter
        return self.query_jobs("SELECT * FROM jobs")
        
    def query_jobs(self, query: str, params: tuple = ()) -> List[JobPosting]:
        """Execute a query and return JobPosting objects."""
        # Store query for debugging/user inspection
        self.last_query = self._format_query_with_params(query, params)
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_job(row) for row in rows]
        finally:
            conn.close()

    def _format_query_with_params(self, query: str, params: tuple) -> str:
        """Helper to format query with parameters for display."""
        try:
            # Simple variable substitution for display purposes only
            # This is NOT for execution, so simplistic replacement is okay
            formatted = query
            for param in params:
                val = f"'{param}'" if isinstance(param, str) else str(param)
                formatted = formatted.replace('?', val, 1)
            return formatted
        except:
            return f"{query} | Params: {params}"

    def _row_to_job(self, row) -> JobPosting:
        """Convert a DB row to a JobPosting object."""
        return JobPosting(
            id=row['id'],
            title=row['title'],
            institution=row['institution'],
            department=row['department'],
            division=row['division'],
            section=row['section'],
            location=row['location'],
            description=row['description'],
            salary_range=row['salary_range'],
            keywords=row['keywords'],
            deadline=row['deadline'],
            date_active=row['date_active'],
            year=row['year'],
            source_file=row['source_file'],
            jel_classification=row['jel_classification'] or ''
        )

    # Filtering methods using SQL
    def get_by_year(self, year: str) -> List[JobPosting]:
        return self.query_jobs("SELECT * FROM jobs WHERE year = ?", (year,))

    def get_by_institution(self, institution: str) -> List[JobPosting]:
        return self.query_jobs("SELECT * FROM jobs WHERE institution LIKE ?", (f"%{institution}%",))
        
    def get_by_country(self, country: str) -> List[JobPosting]:
        return self.query_jobs("SELECT * FROM jobs WHERE location LIKE ?", (f"%{country}%",))

    def get_by_state(self, state: str) -> List[JobPosting]:
        return self.query_jobs("SELECT * FROM jobs WHERE location LIKE ?", (f"%{state}%",))

    # Metadata methods
    def get_years(self) -> List[str]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT year FROM jobs WHERE year IS NOT NULL ORDER BY year DESC")
            return [str(row[0]) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_institutions(self) -> List[str]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT institution FROM jobs WHERE institution IS NOT NULL ORDER BY institution")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_states(self) -> List[str]:
        """Return list of states (parsing locations)."""
        # For now, return empty list or simple extraction 
        return [] 

    def get_countries(self) -> List[str]:
        # Since we don't have strict country column, we might return known locations or rely on raw strings
        # For now, simplistic approach
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT location FROM jobs WHERE location IS NOT NULL")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_schema_string(self) -> str:
        """Get database schema as a string for LLM context."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='jobs'")
            result = cursor.fetchone()
            if result:
                return result[0]
            return "Table 'jobs' not found."
        except Exception as e:
            logger.error(f"Error getting schema: {e}")
            return "Error retrieving schema."
        finally:
            conn.close()

    def execute_raw_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute raw SQL query and return dicts (good for aggregations)."""
        # Capture for debug
        self.last_query = self._format_query_with_params(query, params)
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
