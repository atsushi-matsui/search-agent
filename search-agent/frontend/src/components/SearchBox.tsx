import { useState, useRef, useEffect } from 'react';

interface SearchBoxProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
  suggestions?: string[];
}

const EXAMPLE_QUERIES = [
  'なんとなくワクワクする映画',
  '心がほっこりする作品',
  '雨の日に見たい映画',
  'デート向けのロマンチックな映画',
  'アドレナリンが出るアクション',
  '泣ける感動作',
  '頭を使わずに楽しめる映画',
  '夜中にひとりで見たいホラー',
];

export default function SearchBox({ onSearch, isLoading, suggestions = [] }: SearchBoxProps) {
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim());
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    onSearch(suggestion);
    setShowSuggestions(false);
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (inputRef.current && !inputRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const displaySuggestions = suggestions.length > 0 ? suggestions : EXAMPLE_QUERIES;

  return (
    <div className="relative w-full max-w-3xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div
          className={`relative flex items-center bg-surface rounded-lg border-2 transition-all duration-300 ${
            isFocused ? 'border-brand shadow-lg shadow-brand/20' : 'border-gray-200 shadow-sm'
          }`}
        >
          <svg
            className="absolute left-4 w-5 h-5 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => {
              setIsFocused(true);
              setShowSuggestions(true);
            }}
            onBlur={() => setIsFocused(false)}
            placeholder="どんな気分の映画を探していますか？"
            className="w-full bg-transparent text-gray-900 text-lg py-4 pl-12 pr-32 focus:outline-none placeholder-gray-400"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className={`absolute right-2 px-6 py-2 rounded-md font-medium transition-all duration-300 ${
              isLoading || !query.trim()
                ? 'bg-gray-200 text-gray-600 cursor-not-allowed'
                : 'bg-brand hover:bg-brand-hover text-white'
            }`}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                検索中
              </span>
            ) : (
              '検索'
            )}
          </button>
        </div>
      </form>

      {showSuggestions && !isLoading && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-surface/95 backdrop-blur-sm rounded-lg border border-gray-200 shadow-xl z-10 overflow-hidden">
          <div className="p-3 border-b border-gray-200">
            <span className="text-xs text-gray-500 uppercase tracking-wider">
              {suggestions.length > 0 ? '最近の検索' : '検索例'}
            </span>
          </div>
          <div className="max-h-64 overflow-y-auto">
            {displaySuggestions.map((suggestion, index) => (
              <button
                key={index}
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSuggestionClick(suggestion);
                }}
                className="w-full px-4 py-3 text-left text-gray-700 hover:bg-surface-muted/50 hover:text-gray-900 transition flex items-center gap-3"
              >
                <svg
                  className="w-4 h-4 text-gray-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  {suggestions.length > 0 ? (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  ) : (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  )}
                </svg>
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
