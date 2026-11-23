<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { RouteLocationRaw } from 'vue-router';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import ManualAmountNote from '@/modules/balances/components/ManualAmountNote.vue';
import { type AssetComparison, reconciliationAssetQuery } from '@/modules/balances/view/history-comparison';
import { useBalanceView } from '@/modules/balances/view/use-balance-view';
import { useBalanceViewData } from '@/modules/balances/view/use-balance-view-data';
import { reconciliationRoute } from '@/modules/history/reconciliation/routes';

const { identifier, isCollectionParent = false } = defineProps<{
  identifier: string;
  isCollectionParent?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { getAssetField } = useAssetInfoRetrieval();
const { available } = useBalanceView();
const { comparable, getAssetComparison, isHistory } = useBalanceViewData();

const reconciliationLink = computed<RouteLocationRaw>(() =>
  reconciliationRoute(reconciliationAssetQuery(identifier, isCollectionParent, getAssetField(identifier, 'symbol'))));
const comparison = computed<AssetComparison>(() => getAssetComparison(identifier, isCollectionParent));
const show = computed<boolean>(() => get(available) && get(comparable));
/** The amount under the view the page is not showing. */
const otherAmount = computed<BigNumber>(() => (get(isHistory) ? get(comparison).queried : get(comparison).history));
const differs = computed<boolean>(() => !get(comparison).delta.isZero());
const hasManual = computed<boolean>(() => get(differs) && get(comparison).manual.gt(0));
</script>

<template>
  <div
    v-if="show"
    class="flex flex-col gap-0.5 text-xs text-rui-text-secondary"
    data-testid="asset-view-comparison"
  >
    <div class="flex flex-wrap items-center gap-x-1">
      <span>{{ isHistory ? t('balance_view.live') : t('balance_view.from_history') }}</span>
      <AssetAmountDisplay
        :amount="otherAmount"
        :asset="identifier"
        no-truncate
      />
      <RouterLink
        v-if="differs"
        :to="reconciliationLink"
        class="flex items-center gap-x-1 font-medium text-rui-warning"
        data-testid="asset-view-comparison-delta"
      >
        <AssetAmountDisplay
          :amount="comparison.delta"
          :asset="identifier"
          no-truncate
        />
      </RouterLink>
    </div>
    <ManualAmountNote
      v-if="hasManual"
      :amount="comparison.manual"
      :asset="identifier"
      data-testid="asset-view-comparison-manual"
    />
  </div>
</template>
