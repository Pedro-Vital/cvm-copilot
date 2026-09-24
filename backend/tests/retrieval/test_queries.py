from app.retrieval.queries import (
    build_filters,
    build_full_text_search_sql,
    build_semantic_search_sql,
)
from app.retrieval.types import SearchFilters


def test_no_filters() -> None:
    assert build_filters(None) == ("", {})
    assert build_filters(SearchFilters()) == ("", {})


def test_ticker_filter() -> None:
    sql, params = build_filters(SearchFilters(ticker="VALE3"))

    assert sql == " AND sd.ticker = :ticker"
    assert params == {"ticker": "VALE3"}


def test_ticker_and_years_are_anded() -> None:
    sql, params = build_filters(SearchFilters(ticker="SUZB3", fiscal_years=[2021, 2025]))

    assert sql == " AND sd.ticker = :ticker AND sd.fiscal_year = ANY(:fiscal_years)"
    assert params == {"ticker": "SUZB3", "fiscal_years": [2021, 2025]}


def test_empty_years_list_applies_no_filter() -> None:
    assert build_filters(SearchFilters(fiscal_years=[])) == ("", {})


def test_semantic_sql_orders_by_cosine_distance() -> None:
    sql = build_semantic_search_sql(" AND sd.ticker = :ticker")

    assert "ORDER BY dc.embedding <=> CAST(:query_vec AS vector)" in sql
    assert "WHERE TRUE AND sd.ticker = :ticker" in sql
    assert "LIMIT :limit" in sql


def test_full_text_sql_ors_portuguese_lexemes() -> None:
    sql = build_full_text_search_sql("")

    # Must match the generated search_vector column's config.
    assert "to_tsvector('portuguese', :query_text)" in sql
    assert "' | '" in sql
    assert ")::tsquery" in sql
    assert "ORDER BY ts_rank_cd(dc.search_vector, q.query) DESC" in sql
