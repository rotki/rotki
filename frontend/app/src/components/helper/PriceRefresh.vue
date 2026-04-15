<script setup lang="ts">
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useSectionStatus } from '@/composables/status';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { Section } from '@/modules/common/status';
import { usePriceRefresh } from '@/modules/prices/use-price-refresh';

const emit = defineEmits<{
  click: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { refreshPrices } = usePriceRefresh();
const { isLoading: refreshing } = useSectionStatus(Section.PRICES);
const { loadingBalances } = useBalancesLoading();
const { assets } = useAggregatedBalances();
const disabled = computed<boolean>(() => get(refreshing) || get(loadingBalances));

async function refresh() {
  emit('click');
  await refreshPrices(true, get(assets));
}
</script>

<template>
  <RuiButton
    variant="outlined"
    color="primary"
    :loading="refreshing"
    data-cy="price-refresh"
    :disabled="disabled"
    @click="refresh()"
  >
    <template #prepend>
      <RuiIcon name="lu-refresh-ccw" />
    </template>
    {{ t('price_refresh.button') }}
  </RuiButton>
</template>
