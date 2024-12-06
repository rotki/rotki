/**
 * Keeps track of a shared, global instance of the items per page setting.
 *
 * It is shared between the main.ts and settings store, because referencing the store
 * directly, creates issues with tracking.
 */
export const useItemsPerPage = createSharedComposable(() => ref<number>(10));
