import type { ShallowRef } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { DIALOG_TYPES, type DialogShowOptions, type DialogType } from '@/modules/history/events/dialog-types';

/**
 * Query keys other pages navigate here with to land on a particular dialog, e.g. a decoding-status
 * link from the task center, or a row of the global action center. They are one-shot instructions
 * rather than view state, which is why they are cleared below instead of being persisted like the
 * table's own query keys.
 */
const QUERY_TO_DIALOG = {
  openCustomizedEventDuplicatesDialog: { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES },
  openDecodingStatusDialog: { type: DIALOG_TYPES.DECODING_STATUS },
  openInternalTxConflictsDialog: { type: DIALOG_TYPES.INTERNAL_TX_CONFLICTS },
  openMatchAssetMovementsDialog: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS },
  openMatchBridgesDialog: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS },
} as const satisfies Record<string, DialogShowOptions>;

type DialogQueryKey = keyof typeof QUERY_TO_DIALOG;

/** A dialog another page can land on by navigating to the history events page. */
export type RoutableDialogType = (typeof QUERY_TO_DIALOG)[DialogQueryKey]['type'];

function isDialogQueryKey(key: string): key is DialogQueryKey {
  return key in QUERY_TO_DIALOG;
}

export function isRoutableDialogType(type: DialogType): type is RoutableDialogType {
  return Object.values(QUERY_TO_DIALOG).some(options => options.type === type);
}

/** The route that lands on the history events page with the given dialog open. */
export function historyDialogRoute(type: RoutableDialogType): RouteLocationRaw {
  const key = Object.keys(QUERY_TO_DIALOG).filter(isDialogQueryKey).find(candidate => QUERY_TO_DIALOG[candidate].type === type);
  return { name: '/history/events/', query: key ? { [key]: 'true' } : {} };
}

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
    const key = Object.keys(query).filter(isDialogQueryKey).find(candidate => query[candidate]);
    if (!key)
      return;

    await nextTick();
    get(container)?.show(QUERY_TO_DIALOG[key]);
    await router.replace({ query: {} });
  });
}
