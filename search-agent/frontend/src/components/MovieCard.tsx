import { useState } from 'react';
import { RankedMovie } from '../types/search';

interface MovieCardProps {
  rankedMovie: RankedMovie;
  rank: number;
}

const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500';

const genreColors: Record<string, string> = {
  'Action': 'bg-red-600',
  'Adventure': 'bg-orange-600',
  'Animation': 'bg-purple-600',
  'Comedy': 'bg-yellow-600',
  'Crime': 'bg-gray-200',
  'Documentary': 'bg-blue-600',
  'Drama': 'bg-indigo-600',
  'Family': 'bg-green-600',
  'Fantasy': 'bg-pink-600',
  'History': 'bg-amber-700',
  'Horror': 'bg-red-900',
  'Music': 'bg-teal-600',
  'Mystery': 'bg-violet-700',
  'Romance': 'bg-rose-600',
  'Science Fiction': 'bg-cyan-600',
  'TV Movie': 'bg-slate-600',
  'Thriller': 'bg-zinc-700',
  'War': 'bg-stone-700',
  'Western': 'bg-yellow-800',
};

export default function MovieCard({ rankedMovie, rank }: MovieCardProps) {
  const { movie, relevance_score, explanation } = rankedMovie;
  const [imageError, setImageError] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const posterUrl = movie.poster_path && !imageError
    ? `${TMDB_IMAGE_BASE}${movie.poster_path}`
    : null;

  const scorePercentage = Math.round(relevance_score * 100);

  return (
    <div
      className="movie-card relative group cursor-pointer"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="relative aspect-[2/3] rounded-md overflow-hidden bg-surface-muted">
        {posterUrl ? (
          <img
            src={posterUrl}
            alt={movie.title}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-surface-muted to-surface">
            <div className="text-center p-4">
              <svg
                className="w-12 h-12 mx-auto text-gray-400 mb-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
                />
              </svg>
              <span className="text-gray-500 text-sm">{movie.title}</span>
            </div>
          </div>
        )}

        <div className="absolute top-2 left-2 bg-brand text-white text-xs font-bold px-2 py-1 rounded">
          #{rank}
        </div>

        <div className="absolute top-2 right-2 bg-black/70 text-white text-xs font-bold px-2 py-1 rounded flex items-center gap-1">
          <svg className="w-3 h-3 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          {movie.vote_average.toFixed(1)}
        </div>

        <div
          className={`absolute inset-0 bg-gradient-to-t from-black via-black/50 to-transparent transition-opacity duration-300 ${
            isHovered ? 'opacity-100' : 'opacity-0'
          }`}
        >
          <div className="absolute bottom-0 left-0 right-0 p-4 text-white">
            <h3 className="text-white font-bold text-lg mb-1 line-clamp-2">
              {movie.title}
            </h3>
            {movie.original_title !== movie.title && (
              <p className="text-gray-400 text-xs mb-2">{movie.original_title}</p>
            )}

            <div className="flex flex-wrap gap-1 mb-2">
              {movie.genres.slice(0, 3).map((genre) => (
                <span
                  key={genre}
                  className={`text-xs px-2 py-0.5 rounded ${
                    genreColors[genre] || 'bg-gray-600'
                  } text-white`}
                >
                  {genre}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 mb-2">
              <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand transition-all duration-500"
                  style={{ width: `${scorePercentage}%` }}
                />
              </div>
              <span className="text-brand text-xs font-bold">
                {scorePercentage}%
              </span>
            </div>

            <p className="text-gray-300 text-xs line-clamp-2">
              {explanation}
            </p>

            <div className="flex gap-2 mt-3">
              {movie.homepage ? (
                <a
                  href={movie.homepage}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 bg-white hover:bg-gray-200 text-black font-bold py-2 rounded flex items-center justify-center gap-1 transition"
                  onClick={(e) => e.stopPropagation()}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  公式サイト
                </a>
              ) : (
                <button
                  className="flex-1 bg-gray-600 text-gray-400 font-bold py-2 rounded flex items-center justify-center gap-1 cursor-not-allowed"
                  disabled
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  リンクなし
                </button>
              )}
              <button className="w-10 h-10 border-2 border-gray-400 hover:border-white rounded-full flex items-center justify-center transition">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
              <button className="w-10 h-10 border-2 border-gray-400 hover:border-white rounded-full flex items-center justify-center transition">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
