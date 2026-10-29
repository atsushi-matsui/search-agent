export interface Movie {
  id: string;
  title: string;
  original_title: string;
  overview: string;
  genres: string[];
  popularity: number;
  vote_average: number;
  poster_path?: string;
  backdrop_path?: string;
  release_date?: string;
  homepage?: string;
}

export interface RankedMovie {
  movie: Movie;
  relevance_score: number;
  es_score: number;
  llm_score: number;
  rank: number;
  explanation: string;
}

export interface AgentTiming {
  agent_name: string;
  duration_ms: number;
  phase: number;
}

export interface SearchResponse {
  query: string;
  session_id: string;
  results: RankedMovie[];
  explanation: string;
  applied_constraints: string[];
  processing_steps: string[];
  agent_timings: AgentTiming[];
  total_duration_ms: number;
}

export type SearchBehavior = 'auto' | 'exploratory' | 'goal_oriented' | 'comparative';

export interface SearchRequest {
  query: string;
  user_id?: string;
  session_id: string;
  size?: number;
  skip_agents?: string[];
  override_search_behavior?: string;
}

export interface QueryHistory {
  query: string;
  result_movie_ids: string[];
  timestamp: string;
}
