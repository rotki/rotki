import type { LocationQuery } from 'vue-router';

interface UseAddQueryReturn {
  /**
   * Opens the dialog when the route carries `?add=`, and clears the query either way.
   *
   * @returns whether the query asked for the dialog
   */
  consumeAddQuery: () => Promise<boolean>;
}

/**
 * The `?add=` deep link the add/edit pages share: the query opens the page's create dialog, and is
 * cleared so a reload does not reopen it.
 *
 * @remarks
 * The query is read and cleared before `onAdd` runs, so a handler seeding the dialog from the link
 * gets the snapshot rather than re-reading a route that is already being replaced. Clearing first
 * also means a handler that throws still leaves a clean url.
 *
 * @param onAdd - opens the dialog, receiving the query the link carried
 * @returns the one call the page makes, usually from `onMounted`
 */
export function useAddQuery(onAdd: (query: LocationQuery) => void | Promise<void>): UseAddQueryReturn {
  const router = useRouter();
  const route = useRoute();

  async function consumeAddQuery(): Promise<boolean> {
    const { query } = get(route);
    if (!query.add)
      return false;

    await router.replace({ query: {} });
    await onAdd(query);
    return true;
  }

  return { consumeAddQuery };
}
