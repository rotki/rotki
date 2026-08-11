<script setup lang="ts">
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const emit = defineEmits<{
  click: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { refreshPrices } = usePriceRefresh();
const { useIsActive } = useTaskCenter();
const refreshing = useIsActive(ActivityKind.PRICES);
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
