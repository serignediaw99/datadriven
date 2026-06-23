import aiohttp
from dataclasses import dataclass, field
from typing import Optional

WORLDCUP_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json"
    "/master/2026/worldcup.json"
)

KNOCKOUT_ROUNDS = {
    "Round of 32", "Round of 16", "Quarter-final",
    "Semi-final", "Match for third place", "Final",
}


@dataclass
class Goal:
    scorer: str
    minute: str


@dataclass
class WCMatch:
    num: int
    round: str
    date: str
    team1: str          # real name in group stage; slot code in unplayed KO
    team2: str
    score1: Optional[int]
    score2: Optional[int]
    group: Optional[str]  # None for knockout
    goals1: list[Goal] = field(default_factory=list)
    goals2: list[Goal] = field(default_factory=list)
    ground: str = ""

    @property
    def is_played(self) -> bool:
        return self.score1 is not None

    @property
    def is_group_stage(self) -> bool:
        return self.group is not None

    @property
    def is_knockout(self) -> bool:
        return self.round in KNOCKOUT_ROUNDS


async def fetch_matches(session: Optional[aiohttp.ClientSession] = None) -> list[WCMatch]:
    close = session is None
    if close:
        session = aiohttp.ClientSession()
    try:
        async with session.get(WORLDCUP_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    finally:
        if close:
            await session.close()

    matches: list[WCMatch] = []
    for i, m in enumerate(data.get("matches", [])):
        score = m.get("score")
        ft = score.get("ft") if isinstance(score, dict) else None

        goals1 = [Goal(g["name"], str(g.get("minute", ""))) for g in m.get("goals1", [])]
        goals2 = [Goal(g["name"], str(g.get("minute", ""))) for g in m.get("goals2", [])]

        matches.append(
            WCMatch(
                num=m.get("num", i + 1),
                round=m["round"],
                date=m.get("date", ""),
                team1=m["team1"],
                team2=m["team2"],
                score1=int(ft[0]) if ft else None,
                score2=int(ft[1]) if ft else None,
                group=m.get("group"),
                goals1=goals1,
                goals2=goals2,
                ground=m.get("ground", ""),
            )
        )
    return matches


def extract_groups(matches: list[WCMatch]) -> dict[str, list[str]]:
    """Return {group_name: [team, ...]} from group-stage matches."""
    groups: dict[str, set[str]] = {}
    for m in matches:
        if m.group:
            groups.setdefault(m.group, set()).add(m.team1)
            groups.setdefault(m.group, set()).add(m.team2)
    return {g: sorted(teams) for g, teams in sorted(groups.items())}


def extract_scorers(matches: list[WCMatch]) -> dict[str, int]:
    """Return {player_name: goals} from all played group matches."""
    tally: dict[str, int] = {}
    for m in matches:
        if m.is_played:
            for g in m.goals1 + m.goals2:
                name = g.scorer.strip()
                if name and not name.startswith("OG"):  # skip own goals
                    tally[name] = tally.get(name, 0) + 1
    return dict(sorted(tally.items(), key=lambda x: -x[1]))
