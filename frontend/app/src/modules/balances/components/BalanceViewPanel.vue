<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { RouteLocationRaw } from 'vue-router';
import { RuiButton, RuiButtonGroup } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import BalanceViewPanelStatus from '@/modules/balances/components/BalanceViewPanelStatus.vue';
import BalanceViewSourceRows from '@/modules/balances/components/BalanceViewSourceRows.vue';
import ManualAmountNote from '@/modules/balances/components/ManualAmountNote.vue';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { BalanceView } from '@/modules/balances/view/balance-view';
import { type AssetComparison, mergeTopGaps, reconciliationAssetQuery } from '@/modules/balances/view/history-comparison';
import { useBalanceView } from '@/modules/balances/view/use-balance-view';
import { useBalanceViewData } from '@/modules/balances/view/use-balance-view-data';
import { reconciliationRoute } from '@/modules/history/reconciliation/routes';

const { asset, isCollectionParent = false } = defineProps<{
  /** When scoped to one asset page, show that asset's comparison instead of portfolio-wide figures. */
  asset?: string;
  isCollectionParent?: boolean;
}>();

/** How many of the largest per-asset gaps the panel lists. */
const TOP_GAPS = 3;

/** A section heading in the figures grid: spans the row, set apart from the rows' secondary text. */
const HEADING = 'col-span-3 mb-1 text-xs font-medium tracking-wide text-rui-text-secondary';

/** The third column's notes: one step quieter than labels, so the amounts lead. */
const NOTE = 'truncate text-xs text-rui-text-disabled';

const { t } = useI18n({ useScope: 'global' });

const { hasData } = storeToRefs(useHistoricalSnapshotStore());

const { setView, view } = useBalanceView();
const { balances, comparisons, getAssetComparison, liabilityComparisons, netWorthDifference, queriedNetWorth } = useBalanceViewData();
const { getAssetField } = useAssetInfoRetrieval();

const historyNetWorth = computed<BigNumber>(() => get(queriedNetWorth).plus(get(netWorthDifference)));
const assetSymbol = computed<string>(() => (asset ? (getAssetField(asset, 'symbol') || asset) : ''));
const assetComparison = computed<AssetComparison | undefined>(() =>
  (asset ? getAssetComparison(asset, isCollectionParent) : undefined));
const showAssetManual = computed<boolean>(() => {
  const current = get(assetComparison);
  return !!current && !current.delta.isZero() && current.manual.gt(0);
});
const collectionAssets = computed<ReadonlySet<string>>(() => new Set(
  get(balances).filter(row => !!row.breakdown).map(row => row.asset),
));
const gaps = computed<[string, AssetComparison][]>(() =>
  (asset ? [] : mergeTopGaps(get(comparisons), get(liabilityComparisons), TOP_GAPS)));

function gapReconciliationLink(gapAsset: string): RouteLocationRaw {
  return reconciliationRoute(reconciliationAssetQuery(
    gapAsset,
    get(collectionAssets).has(gapAsset),
    getAssetField(gapAsset, 'symbol'),
  ));
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
      v-if="hasData && asset && assetComparison"
      class="grid grid-cols-[minmax(0,1fr)_auto_5.5rem] items-baseline gap-x-3 gap-y-1 tabular-nums"
      data-testid="balance-view-panel-asset-figures"
    >
      <h4 :class="HEADING">
        {{ assetSymbol }}
      </h4>
      <span class="text-rui-text-secondary">{{ t('balance_view.from_history') }}</span>
      <ValueDisplay
        class="justify-self-end"
        :value="assetComparison.history"
        :format="{ noRoundingMark: true }"
      />
      <span />
      <span class="text-rui-text-secondary">{{ t('balance_view.live') }}</span>
      <ValueDisplay
        class="justify-self-end"
        :value="assetComparison.queried"
        :format="{ noRoundingMark: true }"
      />
      <span />
      <span class="col-span-3 border-t border-default my-0.5" />
      <span class="font-medium">{{ t('balance_view.difference') }}</span>
      <ValueDisplay
        class="justify-self-end font-medium"
        :class="{ 'text-rui-warning': !assetComparison.delta.isZero() }"
        :value="assetComparison.delta"
        :format="{ noRoundingMark: true }"
        data-testid="balance-view-panel-asset-difference"
      />
      <ManualAmountNote
        v-if="showAssetManual"
        :class="NOTE"
        :amount="assetComparison.manual"
        data-testid="balance-view-panel-asset-manual"
      />
      <span v-else />
    </div>

    <div
      v-else-if="hasData"
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

      <BalanceViewSourceRows />

      <template v-if="gaps.length > 0">
        <h4
          class="mt-3"
          :class="HEADING"
          data-testid="balance-view-panel-gaps"
        >
          {{ t('balance_view.largest_gaps') }}
        </h4>
        <template
          v-for="[gapAsset, comparison] in gaps"
          :key="gapAsset"
        >
          <RouterLink
            :to="{ name: '/assets/[identifier]', params: { identifier: gapAsset }, query: { view: BalanceView.HISTORY } }"
            class="text-rui-primary truncate"
            data-testid="balance-view-panel-gap"
          >
            {{ getAssetField(gapAsset, 'symbol') || gapAsset }}
          </RouterLink>
          <RouterLink
            :to="gapReconciliationLink(gapAsset)"
            class="justify-self-end hover:underline"
            data-testid="balance-view-panel-gap-reconcile"
          >
            <ValueDisplay
              class="text-rui-warning"
              :value="comparison.delta"
              :format="{ noRoundingMark: true }"
            />
          </RouterLink>
          <ManualAmountNote
            v-if="comparison.manual.gt(0)"
            :class="NOTE"
            :amount="comparison.manual"
          />
          <span v-else />
        </template>
      </template>
    </div>

    <BalanceViewPanelStatus
      :asset="asset"
      :is-collection-parent="isCollectionParent"
    />
  </div>
</template>
