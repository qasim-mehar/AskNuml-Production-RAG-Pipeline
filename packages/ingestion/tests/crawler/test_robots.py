"""Robots specs: deny with a reason, wildcard fallback, longest rule wins."""

from uni_rag_ingestion.crawler.domain import decide, parse_robots, robots_url


def test_disallowed_url_is_denied_with_a_reason() -> None:
    rules = parse_robots("User-agent: *\nDisallow: /private/\n")
    decision = decide(rules, "https://example.edu/private/notes.html", "uni-rag-crawler/0.1")
    assert decision.allowed is False
    assert decision.reason == "robots disallow /private/"


def test_allowed_url_and_empty_rule_set_are_permitted() -> None:
    rules = parse_robots("User-agent: *\nDisallow: /private/\nAllow: /\n")
    assert decide(rules, "https://example.edu/public", "bot").allowed is True
    assert decide(parse_robots(""), "https://example.edu/x", "bot").allowed is True


def test_longest_matching_rule_wins_and_allow_breaks_ties() -> None:
    rules = parse_robots("User-agent: *\nDisallow: /\nAllow: /public/\nDisallow: /public/secret\n")
    assert decide(rules, "https://example.edu/public/page", "bot").allowed is True
    assert decide(rules, "https://example.edu/public/secret", "bot").allowed is False


def test_specific_agent_group_beats_wildcard() -> None:
    rules = parse_robots(
        "User-agent: *\nDisallow: /shared\n\nUser-agent: uni-rag-crawler\nDisallow: /bot-only\n"
    )
    assert decide(rules, "https://example.edu/shared", "uni-rag-crawler/0.1").allowed is True
    assert decide(rules, "https://example.edu/bot-only", "uni-rag-crawler/0.1").allowed is False
    assert decide(rules, "https://example.edu/shared", "other-bot").allowed is False


def test_empty_disallow_allows_all_despite_other_rules() -> None:
    rules = parse_robots("User-agent: *\nDisallow: /secret\nDisallow:\n")
    decision = decide(rules, "https://example.edu/secret", "bot")
    assert decision.allowed is True
    assert decision.reason == "robots empty disallow allows all"


def test_query_string_is_part_of_the_robots_match_path() -> None:
    rules = parse_robots("User-agent: *\nDisallow: /search?private=1\n")
    assert decide(rules, "https://example.edu/search?private=1", "bot").allowed is False
    assert decide(rules, "https://example.edu/search?private=0", "bot").allowed is True


def test_robots_url_targets_host_root() -> None:
    assert (
        robots_url("https://example.edu:8443/courses/list") == "https://example.edu:8443/robots.txt"
    )
