import sqlite3
import pandas as pd
import glob
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_NAME = 'jobs.db'
DATA_DIR = os.path.join(os.getcwd(), 'joe_data')

def create_schema(conn):
    """Create the jobs table."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            institution TEXT,
            department TEXT,
            division TEXT,
            section TEXT,
            location TEXT,
            description TEXT,
            salary_range TEXT,
            keywords TEXT,
            deadline DATETIME,
            date_active DATETIME,
            year INTEGER,
            source_file TEXT,
            jel_classification TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_year ON jobs(year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_institution ON jobs(institution)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON jobs(location)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords ON jobs(keywords)")
    
    conn.commit()
    logger.info("Schema created successfully")

def process_files():
    """Read all XLS files and insert into SQLite."""
    files = glob.glob(os.path.join(DATA_DIR, "*.xlsx"))
    logger.info(f"Found {len(files)} XLS files in {DATA_DIR}")
    
    conn = sqlite3.connect(DB_NAME)
    create_schema(conn)
    
    total_records = 0
    
    for file_path in files:
        filename = os.path.basename(file_path)
        logger.info(f"Processing {filename}...")
        
        try:
            df = pd.read_excel(file_path)
            
            # Map columns and transform
            records = []
            for _, row in df.iterrows():
                # Extract year from Date_Active (if valid)
                year = None
                date_active = row.get('Date_Active')
                if pd.notna(date_active):
                    try:
                        year = pd.to_datetime(date_active).year
                    except:
                        pass
                
                # Fallback to current year or other logic if needed
                if not year and pd.notna(row.get('joe_issue_ID')):
                     try:
                         # Try extracting from issue ID like "2025-02"
                         parts = str(row.get('joe_issue_ID')).split('-')
                         if parts and parts[0].isdigit():
                             year = int(parts[0])
                     except:
                         pass

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
                    'source_file': filename,
                    'jel_classification': row.get('JEL_Classifications')
                }
                records.append(record)
            
            # Bulk insert (using pandas to_sql would be easier but manual allows explicit control)
            # Actually, let's use a parameterized query for safety
            cursor = conn.cursor()
            query = """
                INSERT OR REPLACE INTO jobs (
                    id, title, institution, department, division, section, 
                    location, description, salary_range, keywords, 
                    deadline, date_active, year, source_file, jel_classification
                ) VALUES (
                    :id, :title, :institution, :department, :division, :section, 
                    :location, :description, :salary_range, :keywords, 
                    :deadline, :date_active, :year, :source_file, :jel_classification
                )
            """
            cursor.executemany(query, records)
            conn.commit()
            
            logger.info(f"Imported {len(records)} records from {filename}")
            total_records += len(records)
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            
    conn.close()
    logger.info(f"Migration complete! Total records: {total_records}")

if __name__ == '__main__':
    process_files()
