<script setup lang="ts">
import { RuiButton, RuiIcon, RuiProgress } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { type RouteLocationRaw, useRouter } from 'vue-router';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useCurrentHistoricalBalances } from '@/modules/balances/use-current-historical-balances';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { reconciliationAssetQuery } from '@/modules/balances/view/history-comparison';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { historicalBalancesActivity } from '@/modules/history/balances/historical-balances.activity';
import { reconciliationRoute } from '@/modules/history/reconciliation/routes';
import { useBucketReconciliation } from '@/modules/history/reconciliation/use-bucket-reconciliation';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const { asset, isCollectionParent = false } = defineProps<{
  /** When scoped to one asset page, review that asset's reconciliation instead of the summary. */
  asset?: string;
  isCollectionParent?: boolean;
}>();

/** Footer actions share one width, so the status and reconciliation rows line up. */
const ACTION = 'min-w-24 shrink-0';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const { error, hasData, loaded, loading, processingRequired, stale } = storeToRefs(useHistoricalSnapshotStore());

const { getAssetField } = useAssetInfoRetrieval();
/** Backend processing is running, so a missing or stale snapshot is about to change. */
const processing = useTaskCenter().useIsActive(historicalBalancesActivity.kind);
const { refresh, triggerProcessing } = useCurrentHistoricalBalances();
const reconciliation = isAccountingUpdateEnabled() ? useBucketReconciliation() : undefined;

const reconciliationLink = computed<RouteLocationRaw>(() => (asset
  ? reconciliationRoute(reconciliationAssetQuery(asset, isCollectionParent, getAssetField(asset, 'symbol')))
  : reconciliationRoute()));
const behind = computed<boolean>(() => get(processingRequired) || get(stale));
const blockedCount = computed<number>(() => (reconciliation ? get(reconciliation.totals).blocked : 0));
const mismatchedCount = computed<number>(() => (reconciliation ? get(reconciliation.totals).mismatch : 0));
const reconciliationIssues = computed<boolean>(() => get(mismatchedCount) + get(blockedCount) > 0);
</script>

<template>
  <section class="flex flex-col gap-2.5 border-t border-default pt-4">
    <div
      v-if="error"
      class="flex flex-wrap items-center justify-end gap-x-2 gap-y-2 text-rui-error"
      data-testid="balance-view-panel-error"
    >
      <RuiIcon
        name="lu-circle-alert"
        size="16"
        class="shrink-0"
      />
      <span class="grow basis-56">{{ loaded ? t('balance_view.refresh_failed') : t('balance_view.load_failed') }}</span>
      <RuiButton
        size="sm"
        variant="outlined"
        color="error"
        :class="ACTION"
        :loading="loading"
        @click="startPromise(refresh())"
      >
        {{ t('common.actions.retry') }}
      </RuiButton>
    </div>
    <div
      v-else-if="!loaded"
      class="flex items-center gap-2 text-rui-text-secondary"
    >
      <RuiProgress
        circular
        variant="indeterminate"
        size="14"
        thickness="2"
      />
      {{ t('balance_view.loading') }}
    </div>
    <div
      v-else-if="processing"
      class="flex items-center gap-2 text-rui-text-secondary"
      data-testid="balance-view-panel-processing"
    >
      <RuiProgress
        circular
        variant="indeterminate"
        size="14"
        thickness="2"
      />
      {{ t('balance_view.processing') }}
    </div>
    <div
      v-else-if="!hasData && !processingRequired"
      class="flex items-center gap-2 text-rui-text-secondary"
      data-testid="balance-view-panel-no-events"
    >
      <RuiIcon
        name="lu-info"
        size="16"
        class="shrink-0"
      />
      {{ t('balance_view.no_events') }}
    </div>
    <div
      v-else-if="behind"
      class="flex items-center gap-2 text-rui-warning"
      data-testid="balance-view-panel-behind"
    >
      <RuiIcon
        name="lu-triangle-alert"
        size="16"
        class="shrink-0"
      />
      <span class="grow">{{ hasData ? t('balance_view.behind') : t('balance_view.not_processed') }}</span>
      <RuiButton
        size="sm"
        variant="outlined"
        color="warning"
        :class="ACTION"
        data-testid="balance-view-panel-process"
        @click="startPromise(triggerProcessing())"
      >
        {{ t('balance_view.process_now') }}
      </RuiButton>
    </div>
    <div
      v-else
      class="flex items-center gap-2 text-rui-text-secondary"
    >
      <RuiIcon
        name="lu-circle-check"
        size="16"
      />
      {{ t('balance_view.up_to_date') }}
    </div>
    <div class="flex items-center gap-2 text-rui-text-secondary">
      <RuiIcon
        name="lu-git-compare"
        size="16"
        class="shrink-0"
      />
      <span
        class="grow"
        data-testid="balance-view-panel-reconciliation-summary"
      >
        {{ asset
          ? t('data_issues.tabs.reconciliation')
          : reconciliationIssues
            ? t('balance_view.reconciliation_issues', { blocked: blockedCount, mismatched: mismatchedCount })
            : t('balance_view.reconciliation_clear') }}
      </span>
      <RuiButton
        size="sm"
        variant="outlined"
        color="primary"
        :class="ACTION"
        data-testid="balance-view-panel-review"
        @click="startPromise(router.push(reconciliationLink))"
      >
        {{ t('balance_view.review') }}
      </RuiButton>
    </div>
  </section>
</template>
