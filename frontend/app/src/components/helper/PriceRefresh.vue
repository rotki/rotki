<script setup lang="ts">
import { useBalancesLoading } from '@/composables/balances/loading';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { usePriceRefresh } from '@/modules/prices/use-price-refresh';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';

const emit = defineEmits<{
  click: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { refreshPrices } = usePriceRefresh();
const { isLoading } = useStatusStore();
const { loadingBalances } = useBalancesLoading();
const { assets } = useAggregatedBalances();

const refreshing = isLoading(Section.PRICES);
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
