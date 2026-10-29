import { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import HeroSection from './components/HeroSection';
import SearchResults from './components/SearchResults';
import { search, getUserHistory } from './api/search';
import { SearchResponse, SearchBehavior } from './types/search';

const STORAGE_KEY = 'search-agent-user-id';
const PRECISION_MODE_KEY = 'search-agent-precision-mode';
const SEARCH_BEHAVIOR_KEY = 'search-agent-behavior';

// 精密検索OFFでスキップするエージェント（Answerは常に実行）
const PRECISION_AGENTS = ['Rerank'];

function App() {
  const [userId, setUserId] = useState<string>(() => {
    return localStorage.getItem(STORAGE_KEY) || '';
  });
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [recentQueries, setRecentQueries] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [precisionMode, setPrecisionMode] = useState<boolean>(() => {
    const saved = localStorage.getItem(PRECISION_MODE_KEY);
    // デフォルトは高速モード（精密検索OFF）
    return saved ? JSON.parse(saved) : false;
  });
  const [searchBehavior, setSearchBehavior] = useState<SearchBehavior>(() => {
    const saved = localStorage.getItem(SEARCH_BEHAVIOR_KEY);
    return (saved as SearchBehavior) || 'auto';
  });

  const loadRecentQueries = useCallback(async () => {
    if (!userId) return;
    try {
      const history = await getUserHistory(userId, 5);
      setRecentQueries(history.map((h) => h.query));
    } catch {
      console.error('Failed to load recent queries');
    }
  }, [userId]);

  useEffect(() => {
    loadRecentQueries();
  }, [loadRecentQueries]);

  const handleUserIdChange = (newUserId: string) => {
    setUserId(newUserId);
    if (newUserId) {
      localStorage.setItem(STORAGE_KEY, newUserId);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  };

  const handlePrecisionModeChange = (enabled: boolean) => {
    setPrecisionMode(enabled);
    localStorage.setItem(PRECISION_MODE_KEY, JSON.stringify(enabled));
  };

  const handleSearchBehaviorChange = (behavior: SearchBehavior) => {
    setSearchBehavior(behavior);
    localStorage.setItem(SEARCH_BEHAVIOR_KEY, behavior);
  };

  // precisionModeからskipAgentsを計算
  const skipAgents = precisionMode ? [] : PRECISION_AGENTS;

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await search({
        query,
        user_id: userId || undefined,
        session_id: sessionId,
        size: 12,
        skip_agents: skipAgents.length > 0 ? skipAgents : undefined,
        override_search_behavior: searchBehavior !== 'auto' ? searchBehavior : undefined,
      });
      setSearchResponse(response);

      if (userId) {
        setTimeout(loadRecentQueries, 500);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '検索に失敗しました');
      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearSession = () => {
    setSessionId(crypto.randomUUID());
    setSearchResponse(null);
  };

  return (
    <div className="min-h-screen bg-page">
      <Header userId={userId} onUserIdChange={handleUserIdChange} />

      <main>
        <HeroSection
          onSearch={handleSearch}
          isLoading={isLoading}
          recentQueries={recentQueries}
          hasSearched={searchResponse !== null}
          precisionMode={precisionMode}
          onPrecisionModeChange={handlePrecisionModeChange}
          searchBehavior={searchBehavior}
          onSearchBehaviorChange={handleSearchBehaviorChange}
        />

        {error && (
          <div className="px-4 md:px-12 py-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>{error}</span>
              </div>
            </div>
          </div>
        )}

        <SearchResults
          response={searchResponse}
          isLoading={isLoading}
          onClearSession={handleClearSession}
          precisionMode={precisionMode}
          onPrecisionModeChange={handlePrecisionModeChange}
        />
      </main>

      <footer className="px-4 md:px-12 py-8 border-t border-gray-200">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="text-gray-500 text-sm">
              Search Agent - AI映画検索システム
            </div>
            <div className="flex items-center gap-6 text-gray-500 text-sm">
              <span>Powered by Claude AI</span>
              <span>•</span>
              <span>Elasticsearch</span>
              <span>•</span>
              <span>Redis</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
