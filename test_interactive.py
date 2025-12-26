"""Interactive local testing script for the job board bot.

Test the bot's query processing without needing Discord.
"""
import sys
from pathlib import Path
from database import SQLJobDatabase
from query_engine import QueryEngine
from config import Config

def print_header():
    """Print a nice header."""
    print("\n" + "="*70)
    print("JoeBot - Local Testing Interface")
    print("="*70)

def print_result(result):
    """Print query results in a readable format."""
    result_type = result.get('type', 'unknown')
    
    print("\n" + "-"*70)
    
    if result_type == 'count':
        print(f"COUNT RESULT")
        print(f"Message: {result.get('message', 'N/A')}")
        print(f"Count: {result.get('count', 0)}")
        
        filters = result.get('filters', {})
        if any(filters.values()):
            print("\nFilters Applied:")
            for key, value in filters.items():
                if value:
                    print(f"  - {key}: {value}")
    
    elif result_type == 'list':
        print(f"LIST RESULT")
        results = result.get('results', [])
        total = result.get('total_count', len(results))
        print(f"Message: {result.get('message', 'N/A')}")
        print(f"Showing {len(results)} of {total} results:\n")
        
        for i, item in enumerate(results[:10], 1):
            print(f"{i}. {item['name']}")
            print(f"   {item['value']}")
            print()
        
        if total > len(results):
            print(f"... and {total - len(results)} more")
    
    elif result_type == 'stats':
        print(f"STATISTICS RESULT")
        print(f"Message: {result.get('message', 'N/A')}\n")
        
        stats = result.get('stats', {})
        for key, value in list(stats.items())[:15]:
            print(f"  {key}: {value}")
        
        if len(stats) > 15:
            print(f"  ... and {len(stats) - 15} more")
    
    elif result_type == 'help':
        print(f"HELP")
        print(result.get('message', 'No help available'))
    
    elif result_type == 'error':
        print(f"ERROR")
        print(result.get('message', 'Unknown error'))
    
    else:
        print(f"RESULT (type: {result_type})")
        print(result)
    
    print("-"*70)

def interactive_mode(query_engine):
    """Run in interactive mode."""
    print("\nInteractive Mode - Type 'quit' or 'exit' to stop")
    print("Type 'help' for query examples\n")
    
    while True:
        try:
            query = input("Query: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            # Process query
            result = query_engine.process_query(query)
            print_result(result)
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")

def test_mode(query_engine):
    """Run predefined test queries."""
    print("\nTest Mode - Running predefined queries...\n")
    
    test_queries = [
        "how many jobs in 2023",
        "how many jobs in 2024",
        "stats by year",
        "stats by country",
        "list jobs at harvard",
        "help"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[Test {i}/{len(test_queries)}] Query: '{query}'")
        result = query_engine.process_query(query)
        print_result(result)
        
        input("\nPress Enter for next test...")
    
    print("\nAll tests complete!")

def main():
    """Main function."""
    print_header()
    
    try:
        # Load database
        print("\nLoading SQL database...")
        db_path = 'jobs.db'
        print(f"   Database: {db_path}")
        
        db = SQLJobDatabase(db_path)
        # db.load_all() is not needed for SQL adapter, but let's check if we handle it or just skip
        # SQLJobDatabase doesn't have load_all()
        
        total_jobs = len(db.get_all_jobs())
        if total_jobs == 0:
            print("ERROR: No jobs loaded! Check your XML files.")
            sys.exit(1)
        
        print(f"Loaded {total_jobs} job postings")
        print(f"   Years: {', '.join(db.get_years())}")
        print(f"   Institutions: {len(db.get_institutions())}")
        print(f"   Countries: {len(db.get_countries())}")
        
        # Initialize query engine
        print("\nInitializing query engine...")
        qe = QueryEngine(db)
        
        # Check LLM status
        if qe.agent_orchestrator and qe.agent_orchestrator.enabled:
            print(f"Agent mode enabled (model: {Config.AGENT_MODEL})")
        else:
            print("Agent mode disabled - using pattern matching")
        
        print("\n" + "="*70)
        print("Choose mode:")
        print("  1. Interactive Mode (type queries)")
        print("  2. Test Mode (run predefined tests)")
        print("  3. Single Query")
        print("="*70)
        
        choice = input("\nChoice (1/2/3): ").strip()
        
        if choice == '1':
            interactive_mode(qe)
        elif choice == '2':
            test_mode(qe)
        elif choice == '3':
            query = input("\nEnter your query: ").strip()
            if query:
                result = qe.process_query(query)
                print_result(result)
        else:
            print("Invalid choice. Exiting.")
    
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("Make sure you're in the correct directory with XML files.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
