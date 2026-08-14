import type { ShallowRef } from 'vue';
import { DIALOG_TYPES, type DialogShowOptions } from '@/modules/history/events/dialog-types';

/**
 * Query keys other pages navigate here with to land on a particular dialog, e.g. a decoding-status
 * link from the task center. They are one-shot instructions rather than view state, which is why
 * they are cleared below instead of being persisted like the table's own query keys.
 */
const QUERY_TO_DIALOG: Record<string, DialogShowOptions> = {
  openDecodingStatusDialog: { type: DIALOG_TYPES.DECODING_STATUS },
  openMatchAssetMovementsDialog: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS },
  openMatchBridgesDialog: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS },
};

interface DialogOpener {
  show: (options: DialogShowOptions) => void;
}

/**
 * Opens the dialog an incoming route asked for, then drops the key so a back-navigation or a
 * reload does not reopen it.
 *
 * `nextTick` before showing: on the immediate run the container has not mounted yet, so the ref is
 * still null.
 */
export function useHistoryEventsDialogRouting(container: ShallowRef<DialogOpener | null>): void {
  const route = useRoute();
  const router = useRouter();

  watchImmediate(route, async ({ query }) => {
    const key = Object.keys(QUERY_TO_DIALOG).find(candidate => query[candidate]);
    if (!key)
      return;

    await nextTick();
    get(container)?.show(QUERY_TO_DIALOG[key]);
    await router.replace({ query: {} });
  });
}
