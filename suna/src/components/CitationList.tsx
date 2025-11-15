'use client';

import React, { useState } from 'react';
import { ExternalLink, FileText, Globe, BookOpen, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { Citation } from '../lib/citation-extractor';

// =============================================================================
// TypeScript Interfaces
// =============================================================================

export interface CitationListProps {
  citations: Citation[];
  className?: string;
  showFullList?: boolean;
  maxVisible?: number;
  onCitationClick?: (citation: Citation) => void;
}

export interface CitationProps {
  citation: Citation;
  index: number;
  onCitationClick?: (citation: Citation) => void;
  className?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

const getSourceIcon = (sourceType?: string) => {
  switch (sourceType) {
    case 'academic':
      return <BookOpen className="w-4 h-4" />;
    case 'web':
      return <Globe className="w-4 h-4" />;
    case 'document':
      return <FileText className="w-4 h-4" />;
    default:
      return <Info className="w-4 h-4" />;
  }
};

const getSourceTypeLabel = (sourceType?: string): string => {
  switch (sourceType) {
    case 'academic':
      return 'Academic Paper';
    case 'web':
      return 'Web Source';
    case 'document':
      return 'Document';
    case 'internal':
      return 'Internal Source';
    default:
      return 'Source';
  }
};

const formatDate = (dateString?: string): string => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch {
    return dateString;
  }
};

// =============================================================================
// Citation Component (Individual)
// =============================================================================

export function CitationComponent({
  citation,
  index,
  onCitationClick,
  className = ''
}: CitationProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const handleClick = () => {
    if (onCitationClick) {
      onCitationClick(citation);
    }
    setShowDetails(!showDetails);
  };

  const confidenceColor = citation.confidence >= 0.8
    ? 'text-green-500'
    : citation.confidence >= 0.6
      ? 'text-yellow-500'
      : 'text-red-500';

  return (
    <div className={`border border-manus-border rounded-lg p-3 mb-2 hover:bg-manus-surface/50 transition-colors ${className}`}>
      {/* Citation Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded bg-manus-accent text-white text-xs font-semibold">
              {index}
            </span>
            <span className="text-sm text-manus-muted">
              {getSourceTypeLabel(citation.sourceType)}
            </span>
            <div className={`flex items-center gap-1 text-xs ${confidenceColor}`}>
              <div className="w-2 h-2 rounded-full bg-current" />
              <span>{Math.round(citation.confidence * 100)}%</span>
            </div>
          </div>

          <h4 className="font-medium text-manus-text truncate">
            {citation.documentName || 'Unknown Source'}
          </h4>
        </div>

        <button
          onClick={handleClick}
          className="flex items-center gap-1 p-1 rounded hover:bg-manus-border transition-colors"
          aria-label={showDetails ? 'Hide details' : 'Show details'}
        >
          {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Citation Details */}
      {showDetails && (
        <div className="mt-3 space-y-2 border-t border-manus-border pt-3">
          {/* Document URL */}
          {citation.documentUrl && (
            <div className="flex items-center gap-2">
              <ExternalLink className="w-3 h-3 text-manus-muted" />
              <a
                href={citation.documentUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-manus-accent hover:underline break-all"
              >
                View Source
              </a>
            </div>
          )}

          {/* Metadata */}
          <div className="text-xs text-manus-muted space-y-1">
            {citation.metadata.publicationDate && (
              <div>Published: {formatDate(citation.metadata.publicationDate)}</div>
            )}

            {citation.metadata.author && (
              <div>Author: {citation.metadata.author}</div>
            )}

            {citation.metadata.title && citation.metadata.title !== citation.documentName && (
              <div>Title: {citation.metadata.title}</div>
            )}

            {citation.metadata.doi && (
              <div>DOI: {citation.metadata.doi}</div>
            )}

            {citation.metadata.pageNumbers && (
              <div>Pages: {citation.metadata.pageNumbers.join('-')}</div>
            )}

            <div>Accessed: {formatDate(citation.metadata.accessDate)}</div>
          </div>

          {/* Text Snippet */}
          {citation.text && (
            <div className="mt-2 p-2 bg-manus-surface rounded border-l-2 border-manus-accent">
              <div className="text-xs text-manus-muted mb-1">Relevant snippet:</div>
              <div className="text-sm text-manus-text italic">
                "{citation.text.length > 200
                  ? `${citation.text.substring(0, 200)}...`
                  : citation.text
                }"
              </div>
              {citation.text.length > 200 && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs text-manus-accent hover:underline mt-1"
                >
                  {isExpanded ? 'Show less' : 'Show more'}
                </button>
              )}
              {isExpanded && (
                <div className="text-sm text-manus-text italic mt-1">
                  "...{citation.text.substring(200)}"
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Citation List Component
// =============================================================================

export function CitationList({
  citations,
  className = '',
  showFullList = false,
  maxVisible = 3,
  onCitationClick
}: CitationListProps) {
  const [isExpanded, setIsExpanded] = useState(showFullList);

  if (!citations || citations.length === 0) {
    return null;
  }

  const visibleCitations = isExpanded ? citations : citations.slice(0, maxVisible);
  const hasMore = citations.length > maxVisible;

  return (
    <div className={`citation-list ${className}`}>
      {/* Citation List Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-manus-text">
          Sources ({citations.length})
        </h3>
        {hasMore && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs text-manus-accent hover:underline flex items-center gap-1"
          >
            {isExpanded ? 'Show less' : `Show ${citations.length - maxVisible} more`}
            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )}
      </div>

      {/* Citations */}
      <div className="space-y-2">
        {visibleCitations.map((citation, index) => (
          <CitationComponent
            key={citation.id}
            citation={citation}
            index={citation.index}
            onCitationClick={onCitationClick}
          />
        ))}
      </div>

      {/* Summary Stats */}
      <div className="mt-4 pt-3 border-t border-manus-border">
        <div className="flex flex-wrap gap-4 text-xs text-manus-muted">
          <div className="flex items-center gap-1">
            <FileText className="w-3 h-3" />
            <span>{citations.filter(c => c.sourceType === 'document').length} Documents</span>
          </div>
          <div className="flex items-center gap-1">
            <Globe className="w-3 h-3" />
            <span>{citations.filter(c => c.sourceType === 'web').length} Web Sources</span>
          </div>
          <div className="flex items-center gap-1">
            <BookOpen className="w-3 h-3" />
            <span>{citations.filter(c => c.sourceType === 'academic').length} Academic</span>
          </div>
          <div className="flex items-center gap-1">
            <span>Avg Confidence: {Math.round(
              citations.reduce((sum, c) => sum + c.confidence, 0) / citations.length * 100
            )}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Inline Citation Component (for use within text)
// =============================================================================

export interface InlineCitationProps {
  citationNumber: number;
  onCitationClick?: (citationNumber: number) => void;
  className?: string;
}

export function InlineCitation({
  citationNumber,
  onCitationClick,
  className = ''
}: InlineCitationProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={() => onCitationClick?.(citationNumber)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`inline-flex items-center justify-center w-5 h-5 rounded bg-manus-surface hover:bg-manus-accent text-manus-accent hover:text-white text-xs font-semibold transition-colors cursor-pointer ${className}`}
      title={`View source [${citationNumber}]`}
      aria-label={`Citation ${citationNumber}`}
    >
      {citationNumber}
    </button>
  );
}

// =============================================================================
// Default Export
// =============================================================================

export default CitationList;