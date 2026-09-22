/**
 * Keeps track of a shared, global instance of the items per page setting.
 *
 * It is shared between the main.ts and settings store, because referencing the store
 * directly, creates issues with tracking.
 */
export const useItemsPerPage = createSharedComposable(() => ref<number>(10));

/** The rows-per-page options every table offers, registered with the RUI table defaults in main.ts. */
export const TABLE_LIMITS: readonly number[] = [10, 25, 50, 100];

/**
 * Whether no rows-per-page choice could change a table of this many rows: every option already fits them all.
 * Only then can a table drop its pagination bars. One that fits a single page only at a raised limit keeps them,
 * or a user who raised the limit past the row count could not lower it again.
 */
export function fitsEveryLimit(rows: number): boolean {
  return rows <= Math.min(...TABLE_LIMITS);
}
