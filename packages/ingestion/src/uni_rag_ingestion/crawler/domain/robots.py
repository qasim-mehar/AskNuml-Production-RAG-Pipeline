"""Pure robots.txt parsing and allow/disallow decisions (L9)."""

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

_ALLOW = "allow"
_DISALLOW = "disallow"
_AGENT = "user-agent"


@dataclass(frozen=True)
class _Rule:
    path: str
    allowed: bool


@dataclass(frozen=True)
class _Group:
    agents: tuple[str, ...]
    rules: tuple[_Rule, ...]
    allow_all: bool = False


@dataclass(frozen=True)
class RobotsRules:
    """Parsed robots groups; an empty rule set means allow everything."""

    groups: tuple[_Group, ...]


@dataclass(frozen=True)
class RobotsDecision:
    """An allow/deny answer plus the human-readable reason for logging."""

    allowed: bool
    reason: str


def robots_url(base_url: str) -> str:
    """Return the canonical robots.txt URL for ``base_url``."""
    parts = urlsplit(base_url)
    return urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))


def parse_robots(text: str) -> RobotsRules:
    """Parse robots.txt lines into agent groups and path rules.

    Consecutive ``User-agent`` lines form one group; following ``Allow`` and
    ``Disallow`` lines apply to every agent in that group. Unknown fields are
    ignored. An empty ``Disallow`` is treated as "allow all".
    """
    agents: list[str] = []
    rules: list[_Rule] = []
    allow_all = False
    groups: list[_Group] = []

    def flush() -> None:
        nonlocal allow_all
        if agents:
            groups.append(_Group(agents=tuple(agents), rules=tuple(rules), allow_all=allow_all))
        agents.clear()
        rules.clear()
        allow_all = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            flush()
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        key = key.strip().lower()
        value = value.strip()
        if key == _AGENT:
            if rules:
                flush()
            agents.append(value.lower())
        elif key in {_ALLOW, _DISALLOW} and agents:
            if key == _DISALLOW and not value:
                allow_all = True
                continue
            rules.append(_Rule(path=value or "/", allowed=key == _ALLOW))

    flush()
    return RobotsRules(groups=tuple(groups))


def decide(rules: RobotsRules, url: str, user_agent: str) -> RobotsDecision:
    """Decide whether ``user_agent`` may fetch ``url`` under ``rules``.

    A group naming the agent exactly (or by substring) beats a wildcard group.
    Within a group the longest matching path wins; ``Allow`` breaks ties.
    """
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    agent = user_agent.lower()
    matching = [
        group
        for group in rules.groups
        if any(pattern == "*" or pattern in agent for pattern in group.agents)
    ]
    if not matching:
        return RobotsDecision(True, "no matching robots group")

    specific = [
        group
        for group in matching
        if any(pattern != "*" and pattern in agent for pattern in group.agents)
    ]
    group = specific[0] if specific else matching[0]
    if group.allow_all:
        return RobotsDecision(True, "robots empty disallow allows all")

    best: _Rule | None = None
    for rule in group.rules:
        if not path.startswith(rule.path):
            continue
        if (
            best is None
            or len(rule.path) > len(best.path)
            or (len(rule.path) == len(best.path) and rule.allowed)
        ):
            best = rule

    if best is None:
        return RobotsDecision(True, "no matching robots rule")
    verb = "allow" if best.allowed else "disallow"
    return RobotsDecision(best.allowed, f"robots {verb} {best.path}")
