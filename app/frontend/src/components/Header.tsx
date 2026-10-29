import { useState } from 'react';

interface HeaderProps {
  userId: string;
  onUserIdChange: (userId: string) => void;
}

export default function Header({ userId, onUserIdChange }: HeaderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [tempUserId, setTempUserId] = useState(userId);

  const handleSave = () => {
    onUserIdChange(tempUserId);
    setIsEditing(false);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-b from-page via-page/80 to-transparent">
      <div className="px-4 md:px-12 py-4 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <h1 className="text-brand text-2xl md:text-3xl font-bold tracking-wider">
            SEARCH AGENT
          </h1>
        </div>

        <div className="flex items-center gap-4">
          {isEditing ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={tempUserId}
                onChange={(e) => setTempUserId(e.target.value)}
                className="bg-surface-muted border border-gray-300 rounded px-3 py-1 text-sm text-gray-900 focus:outline-none focus:border-brand"
                placeholder="ユーザーID"
              />
              <button
                onClick={handleSave}
                className="bg-brand hover:bg-brand-hover text-white px-3 py-1 rounded text-sm font-medium transition"
              >
                保存
              </button>
              <button
                onClick={() => {
                  setTempUserId(userId);
                  setIsEditing(false);
                }}
                className="text-gray-500 hover:text-gray-900 px-2 py-1 text-sm transition"
              >
                キャンセル
              </button>
            </div>
          ) : (
            <div
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition"
            >
              <div className="w-8 h-8 rounded bg-brand flex items-center justify-center">
                <span className="text-white font-bold text-sm">
                  {userId ? userId.charAt(0).toUpperCase() : 'G'}
                </span>
              </div>
              <span className="text-sm text-gray-700 hidden md:inline">
                {userId || 'ゲスト'}
              </span>
              <svg
                className="w-4 h-4 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
