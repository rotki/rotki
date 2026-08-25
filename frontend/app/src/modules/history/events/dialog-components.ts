import type { Component } from 'vue';
import { RuiProgress } from '@rotki/ui-library/components';

/**
 * The dialogs the events page can open, each loaded only once it is asked for. Named exports rather
 * than inline async components in the container, because a spec can only stub what has a name.
 */

/**
 * Shown in a dialog's place while its chunk is still loading.
 *
 * ⚠️ `RuiProgress` must be imported, not named: the Rui resolver only auto-imports into `.vue`, so
 * `h('RuiProgress')` here builds a literal `<ruiprogress>` and the placeholder renders empty.
 */
function DialogLoadingComponent(): ReturnType<typeof h> {
  return h('div', { class: 'flex items-center justify-center p-4' }, h(RuiProgress, { circular: true, size: 40, variant: 'indeterminate' }));
}

/** The delay before the loading placeholder appears, so a fast chunk never flashes one. */
const LOADING_DELAY = 200;

function lazyDialog(loader: () => Promise<{ default: Component }>): Component {
  return defineAsyncComponent({
    delay: LOADING_DELAY,
    loader,
    loadingComponent: DialogLoadingComponent,
  });
}

export const MissingRulesDialog = lazyDialog(async () => import('@/modules/history/management/MissingRulesDialog.vue'));

export const HistoryEventFormDialog = lazyDialog(
  async () => import('@/modules/history/events/HistoryEventFormDialog.vue'),
);

// No placeholder: both status dialogs are small enough that one would only flash.
export const HistoryEventsDecodingStatusDialog: Component = defineAsyncComponent(
  async () => import('@/modules/history/events/HistoryEventsDecodingStatusDialog.vue'),
);

export const HistoryEventsProtocolCacheStatusDialog: Component = defineAsyncComponent(
  async () => import('@/modules/history/events/HistoryEventsProtocolCacheStatusDialog.vue'),
);

export const RepullingTransactionFormDialog = lazyDialog(
  async () => import('@/modules/history/events/tx/RepullingTransactionFormDialog.vue'),
);

export const TransactionFormDialog = lazyDialog(
  async () => import('@/modules/history/events/tx/TransactionFormDialog.vue'),
);

export const AccountingRuleFormDialog = lazyDialog(
  async () => import('@/modules/settings/accounting/rule/AccountingRuleFormDialog.vue'),
);

export const CustomizedEventDuplicatesDialog = lazyDialog(
  async () => import('@/modules/history/events/CustomizedEventDuplicatesDialog.vue'),
);

export const InternalTxConflictsDialog = lazyDialog(
  async () => import('@/modules/history/internal-tx-conflicts/InternalTxConflictsDialog.vue'),
);

export const MatchAssetMovementsDialog = lazyDialog(
  async () => import('@/modules/history/events/MatchAssetMovementsDialog.vue'),
);

export const PotentialMatchesDialog = lazyDialog(
  async () => import('@/modules/history/events/PotentialMatchesDialog.vue'),
);

export const MatchBridgeTransactionsDialog = lazyDialog(
  async () => import('@/modules/history/events/MatchBridgeTransactionsDialog.vue'),
);

export const BridgePotentialMatchesDialog = lazyDialog(
  async () => import('@/modules/history/events/BridgePotentialMatchesDialog.vue'),
);
