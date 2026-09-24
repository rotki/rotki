<script setup lang="ts">
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';

const emit = defineEmits<{
  click: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { refreshing, refreshPrices } = usePriceRefresh();
const { loadingBalances } = useBalancesLoading();
const disabled = computed<boolean>(() => get(refreshing) || get(loadingBalances));

async function refresh() {
  emit('click');
  await refreshPrices(true);
}
</script>

<template>
  <RuiButton
    variant="outlined"
    color="primary"
    size="lg"
    :loading="refreshing"
    data-testid="price-refresh"
    :disabled="disabled"
    @click="refresh()"
  >
    <template #prepend>
      <RuiIcon name="lu-refresh-ccw" />
    </template>
    {{ t('price_refresh.button') }}
  </RuiButton>
</template>
