"""JOE Data Fetcher - Download and process JOE listings from AEA website.

This module downloads the current listings xlsx/xls file from AEA,
parses it, and inserts new listings into the database.
"""
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class JOEDataFetcher:
    """Fetch and process JOE listings from xlsx exports."""
    
    # Default download URL (Native XLS button on https://www.aeaweb.org/joe/listings)
    DEFAULT_XLS_URL = "https://www.aeaweb.org/joe/listings?format=xls"
    
    # Fallback URL (lacks joe_issue_ID column but generally available)
    FALLBACK_XLS_URL = "https://www.aeaweb.org/joe/resultset_xls_output.php?mode=xls_xml"
    
    def __init__(self, database, xls_url: Optional[str] = None, 
                 fallback_url: Optional[str] = None, data_dir: Optional[str] = None):
        """
        Initialize the JOE Data Fetcher.
        
        Args:
            database: SQLJobDatabase instance
            xls_url: URL to download XLS file from (defaults to AEA listings)
            fallback_url: Backup URL if primary fails (defaults to resultset_xls_output)
            data_dir: Directory to store downloaded files (defaults to joe_data/)
        """
        self.db = database
        self.xls_url = xls_url or self.DEFAULT_XLS_URL
        self.fallback_url = fallback_url or self.FALLBACK_XLS_URL
        self.data_dir = Path(data_dir) if data_dir else Path("joe_data")
        self.data_dir.mkdir(exist_ok=True)
        
    def download_current_listings(self, use_fallback: bool = False) -> Path:
        """
        Download the current listings file from AEA.
        
        Args:
            use_fallback: If True, use fallback URL instead of primary
        
        Returns:
            Path to the downloaded file
        """
        url = self.fallback_url if use_fallback else self.xls_url
        logger.info(f"Downloading listings from {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/vnd.ms-excel, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*'
        }
        
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        
        # Check if we got HTML instead of actual XLS (common error)
        content_start = response.content[:50].lower()
        if b'<!doctype' in content_start or b'<html' in content_start:
            if not use_fallback:
                logger.warning(f"Primary URL returned HTML, trying fallback URL...")
                return self.download_current_listings(use_fallback=True)
            else:
                raise ValueError("Both primary and fallback URLs returned HTML instead of XLS")
        
        # Determine file extension from content-type or default to xlsx
        content_type = response.headers.get('Content-Type', '')
        if 'spreadsheet' in content_type or 'xlsx' in content_type:
            ext = '.xlsx'
        elif 'ms-excel' in content_type or 'xls' in content_type:
            ext = '.xls'
        else:
            ext = '.xlsx'  # Default to xlsx
            
        # Save with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suffix = '_fallback' if use_fallback else ''
        filename = f"joe_resultset_{timestamp}{suffix}{ext}"
        file_path = self.data_dir / filename
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Downloaded {len(response.content)} bytes to {file_path}")
        return file_path
    
    def parse_xlsx(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse xlsx/xls file into list of job records.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            List of job record dictionaries
        """
        logger.info(f"Parsing {file_path}")
        
        df = pd.read_excel(file_path)
        records = []
        
        for _, row in df.iterrows():
            # Extract year from Date_Active
            year = None
            date_active = row.get('Date_Active')
            if pd.notna(date_active):
                try:
                    year = pd.to_datetime(date_active).year
                except:
                    pass
            
            # Fallback to issue ID if available (not present in fallback URL exports)
            if not year and 'joe_issue_ID' in row.index and pd.notna(row.get('joe_issue_ID')):
                try:
                    parts = str(row.get('joe_issue_ID')).split('-')
                    if parts and parts[0].isdigit():
                        year = int(parts[0])
                except:
                    pass
            
            # Final fallback to current year
            if not year:
                year = datetime.now().year
            
            record = {
                'id': str(row.get('jp_id', '')),
                'title': row.get('jp_title'),
                'institution': row.get('jp_institution'),
                'department': row.get('jp_department'),
                'division': row.get('jp_division'),
                'section': row.get('jp_section'),
                'location': row.get('locations'),
                'description': row.get('jp_full_text'),
                'salary_range': str(row.get('jp_salary_range')) if pd.notna(row.get('jp_salary_range')) else None,
                'keywords': row.get('jp_keywords'),
                'deadline': row.get('Application_deadline'),
                'date_active': date_active,
                'year': year,
                'source_file': file_path.name,
                'jel_classification': row.get('JEL_Classifications')
            }
            records.append(record)
            
        logger.info(f"Parsed {len(records)} records from {file_path.name}")
        return records
    
    def find_new_listings(self, records: List[Dict]) -> List[Dict]:
        """
        Filter to only new listings not already in database.
        
        Args:
            records: List of job record dictionaries
            
        Returns:
            List of new job records (not in database)
        """
        existing_ids = self.db.get_existing_job_ids()
        new_records = [r for r in records if r['id'] not in existing_ids]
        
        logger.info(f"Found {len(new_records)} new listings out of {len(records)} total")
        return new_records
    
    def insert_new_listings(self, listings: List[Dict]) -> int:
        """
        Insert new listings into the database.
        
        Args:
            listings: List of job record dictionaries
            
        Returns:
            Number of records inserted
        """
        if not listings:
            return 0
            
        count = self.db.bulk_insert_jobs(listings)
        logger.info(f"Inserted {count} new job listings")
        return count
    
    async def run_daily_update(self) -> Dict[str, Any]:
        """
        Main method for daily update routine.
        
        Downloads current listings, checks for new entries,
        and inserts them into the database.
        
        Returns:
            Dictionary with update results
        """
        result = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'downloaded_file': None,
            'total_records': 0,
            'new_count': 0,
            'error': None
        }
        
        try:
            # Download current listings
            file_path = self.download_current_listings()
            result['downloaded_file'] = str(file_path)
            
            # Parse the file
            records = self.parse_xlsx(file_path)
            result['total_records'] = len(records)
            
            # Find new listings
            new_records = self.find_new_listings(records)
            
            # Insert new listings
            inserted = self.insert_new_listings(new_records)
            result['new_count'] = inserted
            result['success'] = True
            
            logger.info(f"Daily update complete: {inserted} new listings added")
            
        except Exception as e:
            logger.error(f"Daily update failed: {e}", exc_info=True)
            result['error'] = str(e)
            
        return result


# Standalone test
if __name__ == '__main__':
    import asyncio
    from database import SQLJobDatabase
    
    logging.basicConfig(level=logging.INFO)
    
    db = SQLJobDatabase()
    fetcher = JOEDataFetcher(db)
    
    result = asyncio.run(fetcher.run_daily_update())
    print(f"Result: {result}")
