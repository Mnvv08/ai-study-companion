import React from 'react';

/**
 * Spinner — consistent loading indicator used across all views.
 * size: 'sm' | 'md' | 'lg'
 */
export function Spinner({ size = 'md', className = '' }) {
  const dim =
    size === 'sm' ? 'h-5 w-5' : size === 'lg' ? 'h-12 w-12' : 'h-8 w-8';
  return (
    <svg
      className={`animate-spin text-indigo-600 ${dim} ${className}`}
      fill="none"
      viewBox="0 0 24 24"
      aria-label="Loading"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v8H4z"
      />
    </svg>
  );
}

/**
 * Centered loading placeholder used when a full section is waiting on data.
 */
export function LoadingPane({ label = 'Loading…' }) {
  return (
    <div className="flex-grow flex flex-col items-center justify-center p-10 text-center">
      <Spinner size="lg" />
      <p className="mt-4 text-sm font-semibold text-gray-700">{label}</p>
    </div>
  );
}

/**
 * Inline error banner — replaces ad-hoc red divs throughout the app.
 */
export function ErrorBanner({ message, className = '' }) {
  if (!message) return null;
  return (
    <div className={`alert-error ${className}`}>
      {message}
    </div>
  );
}

/**
 * Success banner.
 */
export function SuccessBanner({ message, className = '' }) {
  if (!message) return null;
  return (
    <div className={`alert-success ${className}`}>
      {message}
    </div>
  );
}

/**
 * EmptyState — replaces ad-hoc dashed-border placeholder divs.
 */
export function EmptyState({ title, body, action }) {
  return (
    <div className="empty-state">
      {title && <p className="font-semibold text-gray-700 mb-1">{title}</p>}
      {body && <p className="text-xs text-gray-400 mt-1">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/**
 * Score badge — colour-codes a percentage score automatically.
 */
export function ScoreBadge({ score }) {
  const pct = Math.round(score * 100);
  const cls =
    score >= 0.7
      ? 'score-badge-green'
      : score >= 0.4
      ? 'score-badge-yellow'
      : 'score-badge-red';
  return <span className={cls}>{pct}%</span>;
}
