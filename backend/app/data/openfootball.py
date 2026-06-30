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
    score1: Optional[int]   # full-time (90') score
    score2: Optional[int]
    group: Optional[str]  # None for knockout
    goals1: list[Goal] = field(default_factory=list)
    goals2: list[Goal] = field(default_factory=list)
    ground: str = ""
    # Knockout tie-breakers (None when not applicable). et = after extra time,
    # pen = penalty shootout. A KO match's winner is decided by pens, then ET, then ft.
    et1: Optional[int] = None
    et2: Optional[int] = None
    pen1: Optional[int] = None
    pen2: Optional[int] = None

    @property
    def is_played(self) -> bool:
        return self.score1 is not None

    @property
    def is_group_stage(self) -> bool:
        return self.group is not None

    @property
    def is_knockout(self) -> bool:
        return self.round in KNOCKOUT_ROUNDS

    def knockout_winner(self) -> Optional[str]:
        """
        Name of the team that actually advanced from a played knockout match.
        Resolves draws by penalties, then extra time, then full-time. Returns None
        if the match isn't played or the result is genuinely undecided (no field
        separates the teams — shouldn't happen for a finished KO match).
        """
        if not self.is_played:
            return None
        if self.pen1 is not None and self.pen2 is not None and self.pen1 != self.pen2:
            return self.team1 if self.pen1 > self.pen2 else self.team2
        a = self.et1 if self.et1 is not None else self.score1
        b = self.et2 if self.et2 is not None else self.score2
        if a is None or b is None or a == b:
            return None
        return self.team1 if a > b else self.team2


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
        score = m.get("score") if isinstance(m.get("score"), dict) else {}
        ft = score.get("ft")
        et = score.get("et")
        pen = score.get("p")

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
                et1=int(et[0]) if et else None,
                et2=int(et[1]) if et else None,
                pen1=int(pen[0]) if pen else None,
                pen2=int(pen[1]) if pen else None,
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
