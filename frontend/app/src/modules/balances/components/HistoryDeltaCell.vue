<script setup lang="ts">
import type { AssetComparison } from '@/modules/balances/view/history-comparison';
import { ValueDisplay } from '@/modules/assets/amount-display/components';

const { comparison } = defineProps<{
  /** Absent when the asset has no comparison, which renders nothing. */
  comparison?: AssetComparison;
}>();

const { t } = useI18n({ useScope: 'global' });

const differs = computed<boolean>(() => !!comparison && !comparison.delta.isZero());
const hasManual = computed<boolean>(() => !!comparison && comparison.manual.gt(0));
/** Every unit the queried side holds is manual, so history was never going to see it. */
const allManual = computed<boolean>(() => !!comparison && get(hasManual) && comparison.manual.gte(comparison.queried));
</script>

<template>
  <div
    v-if="differs && comparison"
    class="flex flex-col items-end text-xs"
    data-testid="history-delta-cell"
  >
    <ValueDisplay
      class="text-rui-warning font-medium"
      :value="comparison.delta"
    />
    <span
      v-if="allManual"
      class="text-rui-text-secondary"
      data-testid="history-delta-cell-all-manual"
    >
      {{ t('balance_view.all_manual') }}
    </span>
    <i18n-t
      v-else-if="hasManual"
      scope="global"
      keypath="balance_view.manual_amount"
      tag="span"
      class="text-rui-text-secondary"
      data-testid="history-delta-cell-manual"
    >
      <template #amount>
        <ValueDisplay
          class="inline"
          :value="comparison.manual"
        />
      </template>
    </i18n-t>
  </div>
</template>
