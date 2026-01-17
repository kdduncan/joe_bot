"""Quick test of the JOE Data Fetcher."""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from joe_data_fetcher import JOEDataFetcher
from database import SQLJobDatabase

async def main():
    db = SQLJobDatabase()
    fetcher = JOEDataFetcher(db)
    
    # Get baseline count
    existing_ids = db.get_existing_job_ids()
    print(f"Existing jobs: {len(existing_ids)}")
    
    # Run update
    result = await fetcher.run_daily_update()
    
    print(f"Result:")
    print(f"  Success: {result['success']}")
    print(f"  Total records in file: {result['total_records']}")
    print(f"  New listings added: {result['new_count']}")
    if result.get('error'):
        print(f"  Error: {result['error']}")

if __name__ == '__main__':
    asyncio.run(main())
