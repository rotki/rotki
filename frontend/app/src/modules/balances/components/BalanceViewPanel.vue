<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { RouteLocationRaw } from 'vue-router';
import type { AssetComparison } from '@/modules/balances/view/history-comparison';
import { startPromise } from '@shared/utils';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useCurrentHistoricalBalances } from '@/modules/balances/use-current-historical-balances';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { BalanceView } from '@/modules/balances/view/balance-view';
import { useBalanceView } from '@/modules/balances/view/use-balance-view';
import { useBalanceViewData } from '@/modules/balances/view/use-balance-view-data';
import { type SourceDifference, useSourceDifferences } from '@/modules/dashboard/holdings/use-history-holdings-contributions';
import { useSourceKindLabel } from '@/modules/dashboard/holdings/use-source-kind-label';
import { historicalBalancesActivity } from '@/modules/history/balances/historical-balances.activity';
import { useBucketReconciliation } from '@/modules/history/reconciliation/use-bucket-reconciliation';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** How many of the largest per-asset gaps the panel lists. */
const TOP_GAPS = 3;

/** A section heading in the figures grid: spans the row, set apart from the rows' secondary text. */
const HEADING = 'col-span-3 mb-1 text-xs font-medium tracking-wide text-rui-text-secondary';

/** The third column's notes: one step quieter than labels, so the amounts lead. */
const NOTE = 'truncate text-xs text-rui-text-disabled';

/** Footer actions share one width, so the status and reconciliation rows line up. */
const ACTION = 'min-w-24 shrink-0';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const { setView, view } = useBalanceView();
const { comparisons, netWorthDifference, queriedNetWorth } = useBalanceViewData();
const historyNetWorth = computed<BigNumber>(() => get(queriedNetWorth).plus(get(netWorthDifference)));
const sources = useSourceDifferences();
const kindLabel = useSourceKindLabel();
const { getAssetField } = useAssetInfoRetrieval();
const { error, hasData, loaded, loading, processingRequired, stale } = storeToRefs(useHistoricalSnapshotStore());
/** Backend processing is running, so a missing or stale snapshot is about to change. */
const processing = useTaskCenter().useIsActive(historicalBalancesActivity.kind);
const { refresh, triggerProcessing } = useCurrentHistoricalBalances();
const { totals } = useBucketReconciliation();

const reconciliationLink: RouteLocationRaw = {
  name: '/history/data-issues/[[tab]]',
  params: { tab: 'reconciliation' },
};

const gaps = computed<[string, AssetComparison][]>(() => [...get(comparisons)]
  .filter(([, comparison]) => !comparison.delta.isZero())
  .sort(([, a], [, b]) => b.valueDelta.abs().comparedTo(a.valueDelta.abs()) ?? 0)
  .slice(0, TOP_GAPS));

const behind = computed<boolean>(() => get(processingRequired) || get(stale));
const reconciliationIssues = computed<boolean>(() => get(totals).mismatch + get(totals).blocked > 0);

function basisLabel({ basis }: SourceDifference): string {
  if (basis === 'derived')
    return t('balance_view.basis_derived');
  return basis === 'queried' ? t('balance_view.basis_live') : t('balance_view.not_in_history');
}

function select(value: BalanceView | BalanceView[] | undefined): void {
  const next = Array.isArray(value) ? value[0] : value;
  if (next === BalanceView.QUERIED || next === BalanceView.HISTORY)
    startPromise(setView(next));
}
</script>

<template>
  <div
    class="flex flex-col gap-4 p-4 w-[22rem] text-sm"
    data-testid="balance-view-panel"
  >
    <div class="flex flex-col gap-2">
      <RuiButtonGroup
        :model-value="view"
        variant="segmented"
        required
        size="sm"
        class="w-full [&>*]:flex-1"
        :aria-label="t('balance_view.label')"
        @update:model-value="select($event)"
      >
        <RuiButton
          :model-value="BalanceView.QUERIED"
          data-testid="balance-view-queried"
        >
          {{ t('balance_view.live_balances') }}
        </RuiButton>
        <RuiButton
          :model-value="BalanceView.HISTORY"
          :disabled="!hasData"
          data-testid="balance-view-history"
        >
          {{ t('balance_view.from_event_history') }}
        </RuiButton>
      </RuiButtonGroup>

      <p
        class="grid text-xs text-rui-text-secondary"
        data-testid="balance-view-panel-description"
      >
        <span
          class="col-start-1 row-start-1"
          :class="{ invisible: view !== BalanceView.QUERIED }"
        >
          {{ t('balance_view.live_description') }}
        </span>
        <span
          class="col-start-1 row-start-1"
          :class="{ invisible: view !== BalanceView.HISTORY }"
        >
          {{ t('balance_view.history_description') }}
        </span>
      </p>
    </div>

    <div
      v-if="hasData"
      class="grid grid-cols-[minmax(0,1fr)_auto_5.5rem] items-baseline gap-x-3 gap-y-1 tabular-nums"
      data-testid="balance-view-panel-figures"
    >
      <h4 :class="HEADING">
        {{ t('balance_view.net_worth') }}
      </h4>
      <span class="text-rui-text-secondary">{{ t('balance_view.from_history') }}</span>
      <FiatDisplay
        class="justify-self-end"
        :value="historyNetWorth"
      />
      <span />
      <span class="text-rui-text-secondary">{{ t('balance_view.live') }}</span>
      <FiatDisplay
        class="justify-self-end"
        :value="queriedNetWorth"
      />
      <span />
      <span class="col-span-3 border-t border-default my-0.5" />
      <span class="font-medium">{{ t('balance_view.difference') }}</span>
      <FiatDisplay
        class="justify-self-end font-medium"
        :class="{ 'text-rui-warning': !netWorthDifference.isZero() }"
        :value="netWorthDifference"
        data-testid="balance-view-panel-difference"
      />
      <span />

      <template v-if="sources.length > 0">
        <h4
          class="mt-3"
          :class="[HEADING]"
          data-testid="balance-view-panel-sources"
        >
          {{ t('balance_view.by_source') }}
        </h4>
        <template
          v-for="source in sources"
          :key="source.kind"
        >
          <span class="truncate">{{ kindLabel(source.kind) }}</span>
          <FiatDisplay
            class="justify-self-end"
            :class="{ 'text-rui-warning': source.basis === 'derived' && !source.delta.isZero() }"
            :value="source.delta"
          />
          <span
            :class="NOTE"
            :data-basis="source.basis"
          >
            {{ basisLabel(source) }}
          </span>
        </template>
      </template>

      <template v-if="gaps.length > 0">
        <h4
          class="mt-3"
          :class="[HEADING]"
          data-testid="balance-view-panel-gaps"
        >
          {{ t('balance_view.largest_gaps') }}
        </h4>
        <template
          v-for="[asset, comparison] in gaps"
          :key="asset"
        >
          <RouterLink
            :to="{ name: '/assets/[identifier]', params: { identifier: asset }, query: { view: BalanceView.HISTORY } }"
            class="text-rui-primary truncate"
            data-testid="balance-view-panel-gap"
          >
            {{ getAssetField(asset, 'symbol') || asset }}
          </RouterLink>
          <ValueDisplay
            class="justify-self-end text-rui-warning"
            :value="comparison.delta"
            :format="{ noRoundingMark: true }"
          />
          <i18n-t
            scope="global"
            keypath="balance_view.manual_amount"
            tag="span"
            :class="[NOTE, { invisible: comparison.manual.isZero() }]"
          >
            <template #amount>
              <ValueDisplay
                class="inline"
                :value="comparison.manual"
                :format="{ noRoundingMark: true }"
              />
            </template>
          </i18n-t>
        </template>
      </template>
    </div>

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
        <span class="grow">
          {{ reconciliationIssues
            ? t('balance_view.reconciliation_issues', { blocked: totals.blocked, mismatched: totals.mismatch })
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
  </div>
</template>
