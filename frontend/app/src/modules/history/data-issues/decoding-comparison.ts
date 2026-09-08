import type { DecodingComparisonEvent, TransactionDecodingComparison } from '@/modules/history/data-issues/schemas';

const COMPARISON_FIELDS = [
  'eventType',
  'eventSubtype',
  'amount',
  'asset',
  'balanceEffect',
  'sequenceIndex',
  'timestamp',
  'location',
  'locationLabel',
  'counterparty',
  'address',
  'userNotes',
] as const;

export type ComparisonField = typeof COMPARISON_FIELDS[number];

export interface DecodingEventDiff {
  readonly saved?: DecodingComparisonEvent;
  readonly decoded?: DecodingComparisonEvent;
  readonly fields: ComparisonField[];
  readonly status: 'added' | 'removed' | 'modified' | 'unchanged';
}

function fieldValue(event: DecodingComparisonEvent, field: ComparisonField): string {
  const value = event[field];
  if (field === 'eventSubtype' && (!value || value === 'none'))
    return '';
  return value?.toString() ?? '';
}

function changedFields(saved: DecodingComparisonEvent, decoded: DecodingComparisonEvent): ComparisonField[] {
  return COMPARISON_FIELDS.filter(field => fieldValue(saved, field) !== fieldValue(decoded, field));
}

/**
 * Matches identical events first, then events at the same sequence index.
 *
 * @remarks
 * Customization markers are provenance, not event differences. Unmatched events stay separate
 * additions/removals; array positions are not event identities. An otherwise identical event with
 * a changed sequence index is shown as an order change.
 */
export function diffDecodingEvents(transaction: TransactionDecodingComparison): DecodingEventDiff[] {
  const unmatched = new Set(transaction.decodedEvents);
  const matches = new Map<DecodingComparisonEvent, DecodingComparisonEvent>();
  for (const saved of transaction.savedEvents) {
    const decoded = [...unmatched].find(event => changedFields(saved, event).length === 0);
    if (decoded) {
      matches.set(saved, decoded);
      unmatched.delete(decoded);
    }
  }
  for (const saved of transaction.savedEvents) {
    if (matches.has(saved))
      continue;
    const decoded = [...unmatched].find(event =>
      changedFields(saved, event).every(field => field === 'sequenceIndex'))
    ?? [...unmatched].find(event => event.sequenceIndex === saved.sequenceIndex);
    if (decoded) {
      matches.set(saved, decoded);
      unmatched.delete(decoded);
    }
  }
  const diffs = transaction.savedEvents.map((saved): DecodingEventDiff => {
    const decoded = matches.get(saved);
    if (!decoded)
      return { fields: [], saved, status: 'removed' };
    const fields = changedFields(saved, decoded);
    return { decoded, fields, saved, status: fields.length > 0 ? 'modified' : 'unchanged' };
  });
  return [...diffs, ...Array.from(unmatched, (decoded): DecodingEventDiff => ({ decoded, fields: [], status: 'added' }))];
}
