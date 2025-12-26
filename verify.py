"""Quick verification script to test the bot components."""
import sys
from pathlib import Path

print("=" * 60)
print("JoeBot Verification Script")
print("=" * 60)

# Test 1: Import modules
print("\n[1/5] Testing imports...")
try:
    from database import SQLJobDatabase
    from query_engine import QueryEngine
    from config import Config
    # Disable agent mode for deterministic verification
    Config.USE_AGENT_MODE = False
    print("✓ All modules imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Load SQL database
print("\n[2/5] Loading SQL database...")
try:
    db_path = 'jobs.db'
    db = SQLJobDatabase(db_path)
    
    total_jobs = len(db.get_all_jobs())
    print(f"✓ Loaded {total_jobs} job postings")
    
    if total_jobs == 0:
        print("⚠ Warning: No jobs loaded. Run migrate_data.py first.")
except Exception as e:
    print(f"✗ Database loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test indexing
print("\n[3/5] Testing database indexes...")
try:
    years = db.get_years()
    institutions = db.get_institutions()
    countries = db.get_countries()
    
    print(f"✓ Indexed {len(years)} years: {', '.join(years)}")
    print(f"✓ Indexed {len(institutions)} institutions (sample: {', '.join(list(institutions)[:3])}...)")
    print(f"✓ Indexed {len(countries)} countries (sample: {', '.join(list(countries)[:3])}...)")
except Exception as e:
    print(f"✗ Indexing test failed: {e}")
    sys.exit(1)

# Test 4: Test query engine
print("\n[4/5] Testing query engine...")
try:
    qe = QueryEngine(db)
    
    # Test count query
    if years:
        test_year = years[0]
        result = qe.process_query(f"how many jobs in {test_year}")
        print(f"✓ Count query: Found {result['count']} jobs in {test_year}")
    
    # Test stats query
    result = qe.process_query("stats by year")
    print(f"✓ Stats query: Generated statistics for {len(result['stats'])} years")
    
    # Test help query
    result = qe.process_query("help")
    print(f"✓ Help query: Generated help text")
    
except Exception as e:
    print(f"✗ Query engine test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test specific queries
print("\n[5/5] Testing sample queries...")
try:
    test_queries = [
        "how many job postings in 2023",
        "list jobs in 2024",
        "stats by country",
    ]
    
    for query in test_queries:
        result = qe.process_query(query)
        result_type = result.get('type', 'unknown')
        
        if result_type == 'count':
            print(f"✓ '{query}' -> {result['count']} results")
        elif result_type == 'list':
            print(f"✓ '{query}' -> {result.get('total_count', 0)} results")
        elif result_type == 'stats':
            print(f"✓ '{query}' -> {len(result['stats'])} statistics")
        else:
            print(f"✓ '{query}' -> type: {result_type}")

except Exception as e:
    print(f"✗ Sample queries failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All verification tests passed!")
print("=" * 60)
print("\nNext steps:")
print("1. Create a Discord bot at https://discord.com/developers/applications")
print("2. Copy .env.example to .env and add your bot token")
print("3. Run: python migrate_data.py")
print("4. Run: python test_interactive.py")
print("5. Run: python bot.py")
print("6. Test in Discord: @JoeBot how many jobs in 2024?")
