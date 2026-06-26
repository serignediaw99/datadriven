export interface TeamGroupOdds {
  team: string; p_1st: number; p_2nd: number; p_3rd: number; p_4th: number
  avg_pts: number; avg_gd: number
}
export interface GroupOdds { group: string; teams: TeamGroupOdds[] }
export interface GroupsResponse { groups: GroupOdds[]; n_simulations: number; timestamp: number }

export interface ThirdPlaceOdds {
  group: string; p_qualify_as_3rd: number
  pts_needed_p50: number | null; gd_needed_p50: number | null
}
export interface ThirdPlaceResponse { third_place: ThirdPlaceOdds[]; n_simulations: number; timestamp: number }

export interface KnockoutProbs { R32: number; R16: number; QF: number; SF: number; Final: number; Winner: number }
export interface TeamKnockoutOdds { team: string; probs: KnockoutProbs }
export interface KnockoutResponse { teams: TeamKnockoutOdds[]; n_simulations: number; timestamp: number }

export interface PlayerAwardEntry {
  player: string; team: string; current: number; expected_total: number; p_win: number; p_top5: number
}
export interface AwardsResponse { players: PlayerAwardEntry[]; n_simulations: number; timestamp: number }

export interface ScorelineEntry { score: string; probability: number }
export interface PredictionResponse {
  match_id: number; status: 'played' | 'upcoming'; date?: string
  team1: string; team2: string; result?: string
  xg_home?: number; xg_away?: number
  top_scorelines?: ScorelineEntry[]
  p_home_win?: number; p_draw?: number; p_away_win?: number
  p_over_25?: number; p_btts?: number
  p_clean_sheet_home?: number; p_clean_sheet_away?: number
  most_likely_score?: string; most_likely_score_prob?: number
}
export interface MatchEntry {
  id: number; round: string; group: string | null; date: string
  team1: string; team2: string; score1: number | null; score2: number | null
  status: 'played' | 'upcoming' | 'live'
  live_minute?: number
  live_status?: string
}
export interface MatchesResponse { matches: MatchEntry[] }

export interface BracketSlotTeam { team: string; p_slot: number }
export interface BracketMatch {
  id: number
  match_num?: number
  slot_a?: { desc: string; teams: BracketSlotTeam[] }
  slot_b?: { desc: string; teams: BracketSlotTeam[] }
  team_a: string; team_b: string
  winner: string; p_win: number; p_a_wins: number
  r32_a?: number; r32_b?: number
  r16_a?: number; r16_b?: number
  qf_a?: number; qf_b?: number
}
export interface BracketResponse {
  r32: BracketMatch[]
  r16: BracketMatch[]
  qf: BracketMatch[]
  sf: BracketMatch[]
  final: { team_a: string; team_b: string; winner: string; p_win: number; p_a_wins: number }
}

export interface PathOpponent { opponent: string; p: number }
export interface PathRound { [round: string]: PathOpponent[] }
export interface PathResponse { team: string; path: PathRound }

export interface ScenarioMatchOverride { match_num: number; score1: number; score2: number }
export interface ScenarioRequest { overrides: ScenarioMatchOverride[]; n_sims?: number; focus_team?: string }
export interface ScenarioResponse {
  group_odds: GroupOdds[]; knockout_odds: TeamKnockoutOdds[]
  path?: PathResponse
  n_simulations: number; elapsed_seconds: number
}
