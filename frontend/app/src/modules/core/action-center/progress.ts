import type { ActionItem } from '@/modules/core/action-center/types';

/** The count each row had at one moment, by row id; a row with nothing pending is left out. */
export type CountSnapshot = Readonly<Record<string, number>>;

type CountedRow = Pick<ActionItem<{ kind: string }>, 'id' | 'count' | 'loading'>;

/** The counts worth remembering: every row with something pending. */
export function snapshotCounts(rows: readonly CountedRow[]): CountSnapshot {
  return Object.fromEntries(rows.filter(({ count }) => count > 0).map(({ count, id }) => [id, count]));
}

/**
 * The count each row had at the snapshot, for the rows that are lower now, cleared ones included.
 *
 * @remarks
 * A row that is re-reading is left out, since its count is not an answer yet. A row that grew is left
 * out too: growth is what "new" marks.
 */
export function progressSince(snapshot: CountSnapshot, rows: readonly CountedRow[]): Record<string, number> {
  return Object.fromEntries(rows
    .filter(({ count, id, loading }) => !loading && (snapshot[id] ?? 0) > count)
    .map(({ id }) => [id, snapshot[id]]));
}
