from ai_server_tracker.extract import extract_company_data, html_to_text
from ai_server_tracker.filings import EarningsFiling


def filing(key: str) -> EarningsFiling:
    return EarningsFiling(key, key.upper(), "0001-26-1", "2026-08-01", "2026-07-31", "8-K", "x.htm", "2.02", "https://example.com")


def test_html_to_text_removes_scripts():
    assert html_to_text("<html><script>bad()</script><p>Hello&nbsp;world</p></html>") == "Hello world"


def test_extracts_dell_metrics_without_guessing_missing_values():
    raw = """
    <html><body>
      AI-optimized server orders were $60.9 billion.
      AI-optimized server backlog reached $95 billion.
      AI-optimized server revenue was $16.4 billion.
      Infrastructure Solutions Group revenue was $31.2 billion and Infrastructure Solutions Group operating margin was 15.0%.
    </body></html>
    """
    metrics, _ = extract_company_data(filing("dell"), raw)
    by_name = {metric.metric: metric for metric in metrics}
    assert by_name["ai_server_orders"].value == 60.9e9
    assert by_name["ai_server_backlog"].value == 95e9
    assert by_name["ai_server_revenue"].value == 16.4e9
    assert by_name["isg_operating_margin"].value == 15.0
    assert by_name["isg_operating_income"].value is None
    assert by_name["isg_operating_income"].confidence == "unavailable"


def test_extracts_nvidia_gaap_gross_margin():
    raw = "<p>GAAP gross margin was 75.0%. Data Center revenue was $41.1 billion.</p>"
    metrics, _ = extract_company_data(filing("nvidia"), raw)
    by_name = {metric.metric: metric for metric in metrics}
    assert by_name["gross_margin"].value == 75.0
    assert by_name["data_center_revenue"].value == 41.1e9
