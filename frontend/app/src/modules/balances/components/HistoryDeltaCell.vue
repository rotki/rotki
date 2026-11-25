<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import ManualAmountNote from '@/modules/balances/components/ManualAmountNote.vue';
import { type AssetComparison, reconciliationAssetQuery } from '@/modules/balances/view/history-comparison';
import { reconciliationRoute } from '@/modules/history/reconciliation/routes';

const { asset, comparison, isCollectionParent = false } = defineProps<{
  /** When provided, the delta links to reconciliation filtered to this asset. */
  asset?: string;
  /** Absent when the asset has no comparison, which renders nothing. */
  comparison?: AssetComparison;
  /** True when `asset` represents a folded multi-chain collection so reconciliation matches by symbol. */
  isCollectionParent?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { getAssetField } = useAssetInfoRetrieval();

const differs = computed<boolean>(() => !!comparison && !comparison.delta.isZero());
const hasManual = computed<boolean>(() => !!comparison && comparison.manual.gt(0));
/** Every unit the queried side holds is manual, so history was never going to see it. */
const allManual = computed<boolean>(() => !!comparison && get(hasManual) && comparison.manual.gte(comparison.queried));
const reconciliationLink = computed<RouteLocationRaw | undefined>(() => (asset
  ? reconciliationRoute(reconciliationAssetQuery(asset, isCollectionParent, getAssetField(asset, 'symbol')))
  : undefined));
</script>

<template>
  <div
    v-if="differs && comparison"
    class="flex flex-col items-end text-xs"
    data-testid="history-delta-cell"
  >
    <RouterLink
      v-if="reconciliationLink"
      :to="reconciliationLink"
      class="hover:underline"
      data-testid="history-delta-cell-link"
      @click.stop
    >
      <ValueDisplay
        class="text-rui-warning font-medium"
        :value="comparison.delta"
        :format="{ noRoundingMark: true }"
      />
    </RouterLink>
    <ValueDisplay
      v-else
      class="text-rui-warning font-medium"
      :value="comparison.delta"
      :format="{ noRoundingMark: true }"
    />
    <span
      v-if="allManual"
      class="text-rui-text-secondary"
      data-testid="history-delta-cell-all-manual"
    >
      {{ t('balance_view.all_manual') }}
    </span>
    <ManualAmountNote
      v-else-if="hasManual"
      class="text-rui-text-secondary"
      :amount="comparison.manual"
      data-testid="history-delta-cell-manual"
    />
  </div>
</template>
