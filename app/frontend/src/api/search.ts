import { SearchRequest, SearchResponse, QueryHistory } from '../types/search';

const API_BASE = '/api';

export async function search(request: SearchRequest): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getUserHistory(userId: string, limit = 20): Promise<QueryHistory[]> {
  const response = await fetch(`${API_BASE}/search/user/${userId}/history?limit=${limit}`);

  if (!response.ok) {
    throw new Error(`Failed to get user history: ${response.statusText}`);
  }

  return response.json();
}
