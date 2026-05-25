from convfinqa.application.agent.sql.citation_extractor import extract_citations


def test_extracts_row_and_col_from_eq_predicates() -> None:
    sql = "SELECT value_num FROM cells WHERE row_label='net income' AND col_label='Year ended June 30, 2009'"
    result = extract_citations(sql)
    assert result == [("net income", "Year ended June 30, 2009")]


def test_returns_empty_for_query_with_no_where() -> None:
    result = extract_citations("SELECT value_num FROM cells")
    assert result == []


def test_returns_empty_when_only_row_label_present() -> None:
    result = extract_citations("SELECT value_num FROM cells WHERE row_label='revenue'")
    assert result == []


def test_returns_empty_on_invalid_sql() -> None:
    result = extract_citations("NOT VALID SQL %%% @@!")
    assert result == []


def test_cross_product_with_in_clause_for_col_label() -> None:
    sql = "SELECT value_num FROM cells WHERE row_label='revenue' AND col_label IN ('2008', '2009')"
    result = extract_citations(sql)
    assert set(result) == {("revenue", "2008"), ("revenue", "2009")}


def test_cross_product_with_in_clause_for_row_label() -> None:
    sql = "SELECT SUM(value_num) FROM cells WHERE row_label IN ('item1', 'item2') AND col_label='2009'"
    result = extract_citations(sql)
    assert set(result) == {("item1", "2009"), ("item2", "2009")}


def test_returns_empty_when_col_label_is_non_literal() -> None:
    result = extract_citations("SELECT value_num FROM cells WHERE row_label='revenue' AND col_label=col_label")
    assert result == []
