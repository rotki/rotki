import type { ContextColorsType, RuiIcons } from '@rotki/ui-library';

/** The three directions an event can move balance: incoming, outgoing, or neither. */
export type EventDirection = 'in' | 'out' | 'neutral';

/**
 * Inline arrow shown next to an amount. Vertical arrows follow the table convention used by
 * HistoryEventTypeCombination (out = up, in = down) so the overlay reads as "balance went
 * up/down"; neutral gets a dash, matching the action-menu direction badge.
 */
export function getEventDirectionIcon(direction: EventDirection): RuiIcons {
  switch (direction) {
    case 'in':
      return 'lu-arrow-down';
    case 'out':
      return 'lu-arrow-up';
    case 'neutral':
      return 'lu-minus';
  }
}

/**
 * Canonical in/out/neutral colours, shared with the action menu's HistoryEventActionDirectionBadge:
 * in = success (green), out = error (red), neutral = secondary (grey). These are rotki's app-wide
 * increase/decrease tokens (e.g. AmountDisplayBase's pnl colouring).
 */
export function getEventDirectionColor(direction: EventDirection): ContextColorsType {
  switch (direction) {
    case 'in':
      return 'success';
    case 'out':
      return 'error';
    case 'neutral':
      return 'secondary';
  }
}

/** Text colour class matching {@link getEventDirectionColor}, for use on plain text/icon spans. */
export function getEventDirectionTextClass(direction: EventDirection): string {
  switch (direction) {
    case 'in':
      return 'text-rui-success';
    case 'out':
      return 'text-rui-error';
    case 'neutral':
      return 'text-rui-text-secondary';
  }
}
