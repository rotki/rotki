import type { ContextColorsType } from '@rotki/ui-library';

export const DuplicateHandlingStatus = {
  AUTO_FIX: 'auto-fix',
  MANUAL_REVIEW: 'manual-review',
} as const;

export type DuplicateHandlingStatus = (typeof DuplicateHandlingStatus)[keyof typeof DuplicateHandlingStatus];

export const HISTORY_EVENT_ACTIONS = {
  DECODE: 'decode',
  QUERY: 'query',
  REPULLING: 'repulling',
} as const;

export type HistoryEventAction = typeof HISTORY_EVENT_ACTIONS[keyof typeof HISTORY_EVENT_ACTIONS];

export type HighlightType = ContextColorsType;

export const HIGHLIGHT_CLASSES: Partial<Record<HighlightType, string>> = {
  error: '!bg-rui-error/15',
  success: '!bg-rui-success/15',
  warning: '!bg-rui-warning/15',
};

export function getHighlightClass(highlightType?: HighlightType): string | undefined {
  if (!highlightType)
    return undefined;
  return HIGHLIGHT_CLASSES[highlightType];
}
