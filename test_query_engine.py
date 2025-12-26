"""Tests for query engine module."""
import pytest
from pathlib import Path
from database import SQLJobDatabase
from query_engine import QueryEngine


@pytest.fixture
def database():
    """Fixture to load database once for all tests."""
    db = SQLJobDatabase('jobs.db')
    
    if len(db.get_all_jobs()) == 0:
        pytest.skip("No jobs loaded from XML files")
    
    return db


@pytest.fixture
def query_engine(database):
    """Fixture to create query engine."""
    return QueryEngine(database)


def test_query_engine_initialization(database):
    """Test that QueryEngine can be initialized."""
    qe = QueryEngine(database)
    assert qe.db == database


def test_count_query_by_year(query_engine, database):
    """Test count queries filtered by year."""
    # Get a year that exists in the database
    years = database.get_years()
    if not years:
        pytest.skip("No years available")
    
    test_year = years[0]
    
    query = f"how many jobs in {test_year}"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'count'
    assert 'count' in result
    assert result['count'] > 0
    assert test_year in result.get('filters', {}).get('year', '')
    
    print(f"Query: '{query}' -> Count: {result['count']}")


def test_count_query_total(query_engine, database):
    """Test count query without filters."""
    query = "how many jobs"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'count'
    assert 'count' in result
    assert result['count'] == len(database.get_all_jobs())
    
    print(f"Total jobs: {result['count']}")


def test_count_query_by_institution(query_engine, database):
    """Test count queries filtered by institution."""
    institutions = database.get_institutions()
    if not institutions:
        pytest.skip("No institutions available")
    
    # Find an institution with jobs
    test_inst = None
    for inst in institutions:
        if len(database.get_by_institution(inst)) > 0:
            test_inst = inst
            break
    
    if not test_inst:
        pytest.skip("No suitable institution found")
    
    query = f"how many jobs at {test_inst}"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'count'
    assert result['count'] > 0
    
    print(f"Jobs at {test_inst}: {result['count']}")


def test_list_query(query_engine, database):
    """Test list queries."""
    years = database.get_years()
    if not years:
        pytest.skip("No years available")
    
    test_year = years[0]
    
    query = f"list jobs in {test_year}"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'list'
    assert 'results' in result
    assert len(result['results']) > 0
    
    print(f"List query returned {len(result['results'])} results")


def test_stats_by_year(query_engine):
    """Test statistics by year query."""
    query = "stats by year"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'stats'
    assert 'stats' in result
    assert len(result['stats']) > 0
    
    print(f"Stats by year: {result['stats']}")


def test_stats_by_country(query_engine):
    """Test statistics by country query."""
    query = "breakdown by country"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'stats'
    assert 'stats' in result
    assert len(result['stats']) > 0
    
    print(f"Top countries: {list(result['stats'].keys())[:5]}")


def test_stats_by_institution(query_engine):
    """Test statistics by institution query."""
    query = "stats by institution"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'stats'
    assert 'stats' in result
    assert len(result['stats']) > 0
    
    print(f"Top institutions: {list(result['stats'].keys())[:5]}")


def test_overall_stats(query_engine, database):
    """Test overall statistics query."""
    query = "overall stats"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'stats'
    assert 'stats' in result
    assert 'Total Jobs' in result['stats']
    assert result['stats']['Total Jobs'] == len(database.get_all_jobs())
    
    print(f"Overall stats: {result['stats']}")


def test_help_query(query_engine):
    """Test help query."""
    query = "help"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'help'
    assert 'message' in result
    assert len(result['message']) > 0
    
    print("Help query successful")


def test_combined_filters(query_engine, database):
    """Test queries with combined filters."""
    years = database.get_years()
    countries = database.get_countries()
    
    if not years or not countries:
        pytest.skip("Insufficient data for combined filter test")
    
    test_year = years[0]
    # Find a country with jobs
    test_country = None
    for country in countries:
        if len(database.get_by_country(country)) > 0:
            test_country = country
            break
    
    if not test_country:
        pytest.skip("No suitable country found")
    
    query = f"how many jobs in {test_year} in {test_country}"
    result = query_engine.process_query(query)
    
    assert result['type'] == 'count'
    assert 'count' in result
    
    print(f"Combined filter ({test_year}, {test_country}): {result['count']} jobs")


def test_empty_query(query_engine):
    """Test handling of empty/invalid queries."""
    query = ""
    result = query_engine.process_query(query)
    
    # Should not crash and should return some result
    assert 'type' in result
    
    print(f"Empty query handled: {result['type']}")


def test_year_extraction():
    """Test year extraction from queries."""
    import re
    
    test_cases = [
        ("how many jobs in 2024", "2024"),
        ("jobs from 2023", "2023"),
        ("count 2022 postings", "2022"),
    ]
    
    for query, expected_year in test_cases:
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        assert year_match is not None
        assert year_match.group(0) == expected_year
    
    print("Year extraction tests passed")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
