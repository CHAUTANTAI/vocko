"""Unit tests for news RSS parsing helpers (no MongoDB / network)."""
from src.news_pipeline import _parse_rss_items, _strip_html, _fallback_summary, vietnam_today


SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Thoi su</title>
    <item>
      <title>Hello &amp; Co</title>
      <link>https://vnexpress.net/a.html</link>
      <description>&lt;p&gt;Body &lt;b&gt;text&lt;/b&gt; here&lt;/p&gt;</description>
      <pubDate>Fri, 11 Sep 2026 10:00:00 +0700</pubDate>
    </item>
    <item>
      <title>Second</title>
      <link>https://vnexpress.net/b.html</link>
      <description>Plain</description>
    </item>
    <item>
      <title>Third</title>
      <link>https://vnexpress.net/c.html</link>
      <description>x</description>
    </item>
  </channel>
</rss>
"""


def test_strip_html():
    assert _strip_html("<p>Hi &amp; you</p>") == "Hi & you"


def test_parse_rss_items_limit():
    items = _parse_rss_items(SAMPLE_RSS, limit=2)
    assert len(items) == 2
    assert items[0]["title"] == "Hello & Co"
    assert items[0]["url"] == "https://vnexpress.net/a.html"
    assert items[0]["description"] == "Body text here"
    assert "2026" in items[0]["published_at"]
    assert items[1]["title"] == "Second"


def test_fallback_summary_truncates():
    long = "a" * 500
    out = _fallback_summary(long, "t")
    assert out.endswith("…")
    assert len(out) <= 400


def test_vietnam_today_format():
    d = vietnam_today()
    assert len(d) == 10
    assert d[4] == "-" and d[7] == "-"
