import { AgentTiming, SearchResponse } from "../types/search";
import MovieCard from "./MovieCard";

interface SearchResultsProps {
  response: SearchResponse | null;
  isLoading: boolean;
  onClearSession: () => void;
  precisionMode: boolean;
  onPrecisionModeChange: (enabled: boolean) => void;
}

// 精密検索で追加されるエージェント（Answerは常に実行されるのでここには含めない）
const PRECISION_AGENTS = ["Rerank"];

function LoadingSkeleton() {
  return (
    <div className="px-4 md:px-12 py-8">
      <div className="skeleton h-8 w-64 rounded mb-4" />
      <div className="skeleton h-4 w-96 rounded mb-8" />
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="skeleton aspect-[2/3] rounded-md" />
        ))}
      </div>
    </div>
  );
}

function ProcessingSteps({ steps }: { steps: string[] }) {
  return (
    <div className="bg-surface shadow-sm rounded-lg p-4 mb-6 border border-gray-200">
      <div className="flex items-center gap-2 mb-3">
        <svg
          className="w-5 h-5 text-brand"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        </svg>
        <h3 className="text-gray-900 font-medium">AI処理ステップ</h3>
      </div>
      <div className="space-y-1">
        {steps.map((step, index) => (
          <div key={index} className="flex items-start gap-2 text-sm">
            {step.startsWith("  →") ? (
              <span className="text-gray-500 ml-4">{step}</span>
            ) : (
              <>
                <svg
                  className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="text-gray-700">{step}</span>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function AgentTimingDisplay({
  timings,
  totalDurationMs,
  precisionMode,
  onPrecisionModeChange,
}: {
  timings: AgentTiming[];
  totalDurationMs: number;
  precisionMode: boolean;
  onPrecisionModeChange: (enabled: boolean) => void;
}) {
  const maxDuration = Math.max(...timings.map((t) => t.duration_ms), 1);

  const formatDuration = (ms: number) => {
    if (ms >= 1000) {
      return `${(ms / 1000).toFixed(2)}s`;
    }
    return `${ms.toFixed(0)}ms`;
  };

  const getBarColor = (agentName: string, isSkipped: boolean) => {
    if (isSkipped) return "bg-gray-300";
    const colors: Record<string, string> = {
      ConversationAnalyzer: "bg-purple-500",
      QueryUnderstanding: "bg-blue-500",
      UserPreference: "bg-cyan-500",
      QueryToES: "bg-green-500",
      Retrieval: "bg-yellow-500",
      Rerank: "bg-orange-500",
      Answer: "bg-red-500",
      PreferenceUpdater: "bg-pink-500",
    };
    return colors[agentName] || "bg-gray-500";
  };

  const isPrecisionAgent = (agentName: string) =>
    PRECISION_AGENTS.includes(agentName);

  return (
    <div className="bg-surface shadow-sm rounded-lg p-4 mb-6 border border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-brand"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h3 className="text-gray-900 font-medium">エージェント処理時間</h3>
        </div>
        <span className="text-brand font-bold text-lg">
          合計: {formatDuration(totalDurationMs)}
        </span>
      </div>
      <div className="space-y-2">
        {timings.map((timing) => {
          const isSkipped = timing.duration_ms === 0 && isPrecisionAgent(timing.agent_name);
          return (
            <div key={timing.agent_name} className="flex items-center gap-3">
              <div className="w-8 flex-shrink-0">
                {isPrecisionAgent(timing.agent_name) && (
                  <svg
                    className={`w-4 h-4 ${isSkipped ? "text-gray-400" : "text-brand"}`}
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
                )}
              </div>
              <div className={`w-32 text-sm truncate ${isSkipped ? "text-gray-400" : "text-gray-500"}`}>
                {timing.agent_name}
              </div>
              <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getBarColor(timing.agent_name, isSkipped)} rounded-full transition-all duration-500 flex items-center justify-end pr-2`}
                  style={{
                    width: isSkipped ? "5%" : `${Math.max((timing.duration_ms / maxDuration) * 100, 5)}%`,
                  }}
                >
                  <span className={`text-xs font-medium whitespace-nowrap ${isSkipped ? "text-gray-600" : "text-white"}`}>
                    {isSkipped ? "OFF" : formatDuration(timing.duration_ms)}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {precisionMode ? "精密検索モード: AIが結果を再評価" : "高速検索モード"}
        </span>
        <button
          onClick={() => onPrecisionModeChange(!precisionMode)}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs transition-all ${
            precisionMode
              ? "bg-brand text-gray-900"
              : "bg-gray-200 text-gray-600 hover:bg-gray-300"
          }`}
        >
          <svg
            className="w-3 h-3"
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
          精密検索 {precisionMode ? "ON" : "OFF"}
        </button>
      </div>
    </div>
  );
}

function AppliedConstraints({
  constraints,
  onClear,
}: {
  constraints: string[];
  onClear: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      {constraints.length > 0 && (
        <>
          <span className="text-gray-500 text-sm">適用中の条件:</span>
          {constraints.map((constraint, index) => (
            <span
              key={index}
              className="px-3 py-1 bg-brand/20 text-brand rounded-full text-sm"
            >
              {constraint}
            </span>
          ))}
        </>
      )}
      <button
        onClick={onClear}
        className={`px-3 py-1 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-full text-sm transition ${constraints.length > 0 ? 'ml-2' : ''}`}
      >
        セッションをクリア
      </button>
    </div>
  );
}

export default function SearchResults({
  response,
  isLoading,
  onClearSession,
  precisionMode,
  onPrecisionModeChange,
}: SearchResultsProps) {
  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (!response) {
    return null;
  }

  return (
    <div className="px-4 md:px-12 py-8">
      <div className="mb-6">
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
          「{response.query}」の検索結果
        </h2>
        <p className="text-gray-500 mb-4">
          {response.results.length}件の映画が見つかりました
        </p>
        <AppliedConstraints
          constraints={response.applied_constraints}
          onClear={onClearSession}
        />
      </div>

      {response.explanation && (
        <div className="bg-gradient-to-r from-brand/10 to-transparent border-l-4 border-brand rounded-r-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-brand rounded-full flex items-center justify-center flex-shrink-0">
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-gray-900 font-medium mb-1">AIからのコメント</h3>
              <p className="text-gray-700 text-sm leading-relaxed">
                {response.explanation}
              </p>
            </div>
          </div>
        </div>
      )}

      {response.agent_timings && response.agent_timings.length > 0 && (
        <details className="mb-6">
          <summary className="text-gray-500 text-sm cursor-pointer hover:text-gray-700 transition">
            エージェント処理時間を表示（合計: {response.total_duration_ms ? `${(response.total_duration_ms / 1000).toFixed(2)}s` : '-'}）
          </summary>
          <div className="mt-4">
            <AgentTimingDisplay
              timings={response.agent_timings}
              totalDurationMs={response.total_duration_ms}
              precisionMode={precisionMode}
              onPrecisionModeChange={onPrecisionModeChange}
            />
          </div>
        </details>
      )}

      {response.processing_steps && response.processing_steps.length > 0 && (
        <details className="mb-6">
          <summary className="text-gray-500 text-sm cursor-pointer hover:text-gray-700 transition">
            処理ステップを表示
          </summary>
          <div className="mt-4">
            <ProcessingSteps steps={response.processing_steps} />
          </div>
        </details>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {response.results.map((rankedMovie, index) => (
          <MovieCard
            key={rankedMovie.movie.id}
            rankedMovie={rankedMovie}
            rank={index + 1}
          />
        ))}
      </div>
    </div>
  );
}
