import type { ActionCenterSection, ActionItem, ActionTarget } from '@/modules/core/action-center/types';
import type { ActionCenterOptions } from '@/modules/core/action-center/use-action-center';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { type LocationQuery, useRoute } from 'vue-router';
import { toGlobalTarget } from '@/modules/history/events/actions-center/history-issue-routes';
import { useHistoryEventIssues } from '@/modules/history/events/actions-center/use-history-event-issues';
import { useAccountingRows } from '@/modules/shell/action-center/use-accounting-rows';
import { useAssetRows } from '@/modules/shell/action-center/use-asset-rows';
import { useBinancePairsRows } from '@/modules/shell/action-center/use-binance-pairs-rows';
import { useChainRows } from '@/modules/shell/action-center/use-chain-rows';
import { useGnosisPaySafeRows } from '@/modules/shell/action-center/use-gnosis-pay-safe-rows';
import { useHistorySyncRow } from '@/modules/shell/action-center/use-history-sync-row';
import { useIntegrationRows } from '@/modules/shell/action-center/use-integration-rows';
import { usePremiumRows } from '@/modules/shell/action-center/use-premium-rows';

interface UseGlobalActionRowsReturn {
  /** The history issues, whose busy and checking state the center follows. */
  history: ReturnType<typeof useHistoryEventIssues>;
  /** Every module's rows as their sources raised them, grouped by module, in the fixed section order. */
  raisedGroups: ComputedRef<ActionCenterSection[]>;
  /** How each source behind the rows is re-read. */
  sources: ActionCenterOptions<ActionTarget, string>['sources'];
}

/**
 * The re-scan of a source that history work cannot change, so it is read only on the first scan and
 * when the user asks for a re-scan.
 */
async function noRescan(): Promise<void> {}

/**
 * The rows of every module behind the global action center, and the sources that re-read them.
 *
 * @remarks
 * The sections come in the order their fixes depend on each other: a missing key or indexer leaves the
 * chains and the history behind it incomplete, so keys come first, then chains, then history, then
 * assets. The history rows point at the history events page, keeping its filters when it is open.
 */
export function useGlobalActionRows(): UseGlobalActionRowsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const history = useHistoryEventIssues();
  const historySyncRow = useHistorySyncRow();
  const integrationRows = useIntegrationRows();
  const premiumRows = usePremiumRows();
  const { refresh: refreshBinancePairsRows, rows: binancePairsRows } = useBinancePairsRows();
  const chainRows = useChainRows();
  const { refresh: refreshAssetRows, rows: assetRows } = useAssetRows();
  const { refresh: refreshAccountingRows, rows: accountingRows } = useAccountingRows();
  const { refresh: refreshGnosisPaySafeRows, rows: gnosisPaySafeRows } = useGnosisPaySafeRows();

  const route = useRoute();
  const historyPageQuery = computed<LocationQuery | undefined>(() => (route.name === '/history/events/' ? route.query : undefined));

  const historyRows = computed<ActionItem[]>(() => {
    const pageQuery = get(historyPageQuery);
    return get(history.issues).map(issue => ({
      ...issue,
      checkTarget: toGlobalTarget(issue.checkTarget, pageQuery),
      choices: issue.choices.map(choice => ({ ...choice, target: toGlobalTarget(choice.target, pageQuery) })),
      options: issue.options.map(option => ({ ...option, target: toGlobalTarget(option.target, pageQuery) })),
      target: toGlobalTarget(issue.target, pageQuery),
    }));
  });

  const raisedGroups = computed<ActionCenterSection[]>(() => [
    { id: 'integrations', items: [...get(premiumRows), ...get(integrationRows), ...get(gnosisPaySafeRows), ...get(binancePairsRows)], title: t('action_center.sections.integrations') },
    { id: 'chains', items: get(chainRows), title: t('action_center.sections.chains') },
    { id: 'history', items: [...get(historySyncRow), ...get(historyRows), ...get(accountingRows)], title: t('action_center.sections.history') },
    { id: 'assets', items: get(assetRows), title: t('action_center.sections.assets') },
  ]);

  const sources: ActionCenterOptions<ActionTarget, string>['sources'] = [
    { loading: history.refreshing, refresh: history.refreshAll, rescan: history.rescan },
    { refresh: refreshAssetRows },
    { refresh: refreshBinancePairsRows, rescan: noRescan },
    { refresh: refreshAccountingRows, rescan: noRescan },
    { refresh: refreshGnosisPaySafeRows, rescan: noRescan },
  ];

  return { history, raisedGroups, sources };
}
