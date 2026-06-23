import type {
  GroupsResponse, ThirdPlaceResponse, KnockoutResponse,
  AwardsResponse, PredictionResponse, MatchesResponse, BracketResponse,
  PlayerAwardEntry, PathResponse, ScenarioRequest, ScenarioResponse,
} from './types'

const BASE = import.meta.env.VITE_API_BASE ?? ""

const get = async <T>(path: string): Promise<T> => {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${path} → ${res.status}`)
  return res.json()
}

function sortPlayerAwards(players: PlayerAwardEntry[]): PlayerAwardEntry[] {
  return [...players].sort((a, b) =>
    b.current - a.current || b.expected_total - a.expected_total
  )
}

export const api = {
  groups:     () => get<GroupsResponse>('/api/groups'),
  thirdPlace: () => get<ThirdPlaceResponse>('/api/third-place'),
  knockout:   () => get<KnockoutResponse>('/api/knockout'),
  goldenBoot: async () => {
    const data = await get<AwardsResponse>('/api/awards/golden-boot')
    return { ...data, players: sortPlayerAwards(data.players) }
  },
  topAssists: async () => {
    const data = await get<AwardsResponse>('/api/awards/assists')
    return { ...data, players: sortPlayerAwards(data.players) }
  },
  matches:    () => get<MatchesResponse>('/api/matches'),
  prediction: (id: number) => get<PredictionResponse>(`/api/matches/${id}/prediction`),
  bracket:    () => get<BracketResponse>('/api/bracket'),
  path: (team: string) => get<PathResponse>(`/api/knockout/path/${encodeURIComponent(team)}`),
  scenario: (body: ScenarioRequest): Promise<ScenarioResponse> =>
    fetch(`${BASE}/api/scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() }),
}
