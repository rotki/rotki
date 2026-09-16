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

/** Returns the notes displayed in history, preferring user edits over generated text. */
export function comparisonNotes(event: DecodingComparisonEvent): string | undefined {
  return event.userNotes ?? event.autoNotes;
}

function fieldValue(event: DecodingComparisonEvent, field: ComparisonField): string {
  const value = field === 'userNotes' ? comparisonNotes(event) : event[field];
  if (field === 'eventSubtype' && (!value || value === 'none'))
    return '';
  return value?.toString() ?? '';
}

function changedFields(saved: DecodingComparisonEvent, decoded: DecodingComparisonEvent): ComparisonField[] {
  return COMPARISON_FIELDS.filter(field => fieldValue(saved, field) !== fieldValue(decoded, field));
}

/**
 * The one remaining event that could still be this saved event, if there is exactly one.
 *
 * @remarks
 * Asset and type are what makes two events the same event here, since everything else about them
 * is what the comparison is meant to show. Several candidates mean the pairing would be a guess,
 * so none is returned and they stay separate additions and removals.
 */
function soleCandidate(
  saved: DecodingComparisonEvent,
  unmatched: Set<DecodingComparisonEvent>,
): DecodingComparisonEvent | undefined {
  const candidates = [...unmatched].filter(event =>
    event.asset === saved.asset && event.eventType === saved.eventType);
  return candidates.length === 1 ? candidates[0] : undefined;
}

/**
 * Matches identical events first, then shifted notes edits, then same-asset events at the same
 * order, and finally the one remaining candidate of the same asset and type.
 *
 * @remarks
 * Customization markers are provenance, not event differences. Unmatched events stay separate
 * additions/removals; array positions are not event identities. An otherwise identical event with
 * a changed sequence index and notes is shown as a modification.
 *
 * The last pass exists because a customization commonly edits an amount *and* shifts the index,
 * which the earlier passes both miss: the pair would then render as a removal plus an addition,
 * each carrying its own balance effect, and read as a net double change. It pairs only when a
 * single candidate of that asset and type is left, so an ambiguous set still splits rather than
 * guessing.
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
      changedFields(saved, event).every(field => field === 'sequenceIndex' || field === 'userNotes'))
    ?? [...unmatched].find(event => event.sequenceIndex === saved.sequenceIndex && event.asset === saved.asset);
    if (decoded) {
      matches.set(saved, decoded);
      unmatched.delete(decoded);
    }
  }
  for (const saved of transaction.savedEvents) {
    if (matches.has(saved))
      continue;
    const decoded = soleCandidate(saved, unmatched);
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
