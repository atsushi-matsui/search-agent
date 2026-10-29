import SearchBox from './SearchBox';
import { SearchBehavior } from '../types/search';

interface HeroSectionProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
  recentQueries: string[];
  hasSearched: boolean;
  precisionMode: boolean;
  onPrecisionModeChange: (enabled: boolean) => void;
  searchBehavior: SearchBehavior;
  onSearchBehaviorChange: (behavior: SearchBehavior) => void;
}

const BEHAVIOR_OPTIONS: { value: SearchBehavior; label: string; description: string }[] = [
  { value: 'auto', label: '自動', description: 'AIが判定' },
  { value: 'exploratory', label: '探索的', description: 'LLM検索' },
  { value: 'goal_oriented', label: '目的指向', description: '全文検索' },
  { value: 'comparative', label: '比較', description: 'LLM比較' },
];

export default function HeroSection({
  onSearch,
  isLoading,
  recentQueries,
  hasSearched,
  precisionMode,
  onPrecisionModeChange,
  searchBehavior,
  onSearchBehaviorChange,
}: HeroSectionProps) {
  return (
    <div
      className={`relative transition-all duration-500 ${
        hasSearched ? 'pt-24 pb-8' : 'min-h-[70vh] flex items-center'
      }`}
    >
      <div
        className={`absolute inset-0 bg-gradient-to-b from-page via-surface to-page ${
          hasSearched ? 'opacity-50' : ''
        }`}
      />

      {!hasSearched && (
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0wIDBoNjB2NjBIMHoiLz48cGF0aCBkPSJNMzYgMzRjMC0yLjIxLTEuNzktNC00LTRzLTQgMS43OS00IDQgMS43OSA0IDQgNCA0LTEuNzkgNC00eiIgc3Ryb2tlPSIjMzMzIiBzdHJva2Utd2lkdGg9Ii41Ii8+PC9nPjwvc3ZnPg==')] opacity-10" />
        </div>
      )}

      <div className="relative z-10 w-full px-4 md:px-12">
        <div className={`max-w-4xl mx-auto text-center ${hasSearched ? '' : 'space-y-8'}`}>
          {!hasSearched && (
            <>
              <div className="space-y-4">
                <h1 className="text-4xl md:text-6xl font-bold text-gray-900">
                  あなたの
                  <span className="text-brand">「気分」</span>
                  で探す
                </h1>
                <p className="text-xl md:text-2xl text-gray-700">
                  AI が曖昧な希望から最適な映画を見つけます
                </p>
              </div>

              <div className="flex flex-wrap justify-center gap-3 text-sm">
                <span className="px-4 py-2 bg-surface rounded-full text-gray-700 border border-gray-200">
                  ワクワク
                </span>
                <span className="px-4 py-2 bg-surface rounded-full text-gray-700 border border-gray-200">
                  ほっこり
                </span>
                <span className="px-4 py-2 bg-surface rounded-full text-gray-700 border border-gray-200">
                  スリル
                </span>
                <span className="px-4 py-2 bg-surface rounded-full text-gray-700 border border-gray-200">
                  感動
                </span>
                <span className="px-4 py-2 bg-surface rounded-full text-gray-700 border border-gray-200">
                  癒し
                </span>
              </div>
            </>
          )}

          <SearchBox
            onSearch={onSearch}
            isLoading={isLoading}
            suggestions={recentQueries}
          />

          {!hasSearched && (
            <div className="flex flex-col items-center gap-4 mt-4">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => onPrecisionModeChange(!precisionMode)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm transition-all ${
                    precisionMode
                      ? "bg-brand text-white shadow-lg shadow-brand/30"
                      : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                  }`}
                >
                  <svg
                    className={`w-4 h-4 transition-transform ${precisionMode ? "scale-110" : ""}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                  精密検索{precisionMode ? " ON" : " OFF"}
                </button>
                <span className="text-gray-400 text-xs">
                  {precisionMode ? "AIが結果を再評価・コメント" : "高速検索モード"}
                </span>
              </div>

              {/* 検索行動タイプ選択（検証用） */}
              <div className="flex items-center gap-2">
                <span className="text-gray-500 text-xs">検索タイプ:</span>
                <div className="flex gap-1">
                  {BEHAVIOR_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => onSearchBehaviorChange(option.value)}
                      className={`px-3 py-1 rounded text-xs transition-all ${
                        searchBehavior === option.value
                          ? "bg-blue-600 text-white"
                          : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                      }`}
                      title={option.description}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {!hasSearched && (
            <div className="flex items-center justify-center gap-6 text-gray-500 text-sm">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span>AI解析</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                <span>嗜好学習</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>高速検索</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
