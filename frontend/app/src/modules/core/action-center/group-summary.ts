import { type ActionItem, type ActionUrgency, URGENCY_RANK } from '@/modules/core/action-center/types';

type SummarizedRow = Pick<ActionItem<{ kind: string }>, 'id' | 'urgency' | 'locked' | 'informational'>;

export interface GroupSummary {
  /** how many rows the group holds */
  count: number;
  /** the most pressing urgency among the rows still asking for something; undefined when every row is set aside or locked */
  urgency: ActionUrgency | undefined;
  /** a row the user has not seen yet is among them */
  hasNew: boolean;
}

/**
 * What a folded group still has to say on its header: how many rows it hides, how pressing the most
 * pressing of them is, and whether one of them is new.
 */
export function summarizeGroup(items: readonly SummarizedRow[], newIds: readonly string[]): GroupSummary {
  const urgency = items
    .filter(({ informational, locked }) => !locked && !informational)
    .reduce<ActionUrgency | undefined>(
      (pressing, { urgency }) => (pressing === undefined || URGENCY_RANK[urgency] < URGENCY_RANK[pressing] ? urgency : pressing),
      undefined,
    );

  return {
    count: items.length,
    hasNew: items.some(({ id }) => newIds.includes(id)),
    urgency,
  };
}
