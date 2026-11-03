import type { AsyncComponentLoader, Component, VNode } from 'vue';
import type { assetMovementMatchingKind } from '@/modules/history/events/matching/asset-movement-matching-kind';
import type { bridgeMatchingKind } from '@/modules/history/events/matching/bridge-matching-kind';
import { RuiProgress } from '@rotki/ui-library/components';

/**
 * The dialogs the events page can open, each loaded only once it is asked for. Named exports rather
 * than inline async components in the container, because a spec can only stub what has a name.
 *
 * @packageDocumentation
 */

/**
 * Shown in a dialog's place while its chunk is still loading.
 *
 * `RuiProgress` must be imported, not named: the Rui resolver only auto-imports into `.vue`, so
 * `h('RuiProgress')` here builds a literal `<ruiprogress>` and the placeholder renders empty.
 */
function DialogLoadingComponent(): ReturnType<typeof h> {
  return h('div', { class: 'flex items-center justify-center p-4' }, h(RuiProgress, { circular: true, size: 40, variant: 'indeterminate' }));
}

/** The delay before the loading placeholder appears, so a fast chunk never flashes one. */
const LOADING_DELAY = 200;

function lazyDialog(loader: AsyncComponentLoader): Component {
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

/**
 * A matching dialog with its kind already bound.
 *
 * @remarks
 * The kind is loaded with the dialog, not imported by the container, so a kind's action and row
 * composables stay out of the events page until a matching dialog is opened.
 */
function lazyMatchingDialog(
  loadDialog: () => Promise<{ default: Component }>,
  loadKind: () => Promise<typeof assetMovementMatchingKind | typeof bridgeMatchingKind>,
): Component {
  return lazyDialog(async () => {
    const [{ default: dialog }, kind] = await Promise.all([loadDialog(), loadKind()]);
    return (_: unknown, { attrs }: { attrs: Record<string, unknown> }): VNode => h(dialog, { ...attrs, kind });
  });
}

async function loadMovementKind(): Promise<typeof assetMovementMatchingKind> {
  return (await import('@/modules/history/events/matching/asset-movement-matching-kind')).assetMovementMatchingKind;
}

async function loadBridgeKind(): Promise<typeof bridgeMatchingKind> {
  return (await import('@/modules/history/events/matching/bridge-matching-kind')).bridgeMatchingKind;
}

export const MatchAssetMovementsDialog = lazyMatchingDialog(
  async () => import('@/modules/history/events/UnmatchedMatchingDialog.vue'),
  loadMovementKind,
);

export const PotentialMatchesDialog = lazyMatchingDialog(
  async () => import('@/modules/history/events/PotentialMatchesDialog.vue'),
  loadMovementKind,
);

export const MatchBridgeTransactionsDialog = lazyMatchingDialog(
  async () => import('@/modules/history/events/UnmatchedMatchingDialog.vue'),
  loadBridgeKind,
);

export const BridgePotentialMatchesDialog = lazyMatchingDialog(
  async () => import('@/modules/history/events/PotentialMatchesDialog.vue'),
  loadBridgeKind,
);
