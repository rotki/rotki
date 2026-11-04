<script setup lang="ts">
import ExchangeRefreshMenuItem from '@/modules/balances/exchanges/ExchangeRefreshMenuItem.vue';
import { useLocations } from '@/modules/core/common/use-locations';
import RefreshSplitButton from '@/modules/shell/components/RefreshSplitButton.vue';

const { exchanges, selected, loading = false } = defineProps<{
  exchanges: string[];
  /** The exchange the page shows; the button then refreshes only it. */
  selected?: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'refresh': [];
  'refresh-all': [];
  'refresh-exchange': [exchange: string];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getExchangeName } = useLocations();

const tooltip = computed<string>(() => selected
  ? t('exchange_balances.refresh_menu.exchange', { exchange: getExchangeName(selected) })
  : t('exchange_balances.refresh_menu.all'));
</script>

<template>
  <RefreshSplitButton
    test-id="refresh-exchange-balances"
    :menu-label="t('exchange_balances.refresh_menu.title')"
    :tooltip="tooltip"
    :loading="loading"
    :disabled="exchanges.length === 0"
    :menu-disabled="exchanges.length === 0"
    @refresh="emit('refresh')"
  >
    <template #default="{ close }">
      <div class="w-72 max-w-full py-1">
        <RuiButton
          variant="list"
          :disabled="loading"
          data-testid="refresh-exchange-menu-all"
          @click="close(); emit('refresh-all')"
        >
          <template #prepend>
            <RuiIcon
              size="18"
              name="lu-refresh-ccw"
            />
          </template>
          {{ t('exchange_balances.refresh_menu.all') }}
        </RuiButton>
        <RuiDivider class="my-1" />
        <div class="px-4 pt-1 pb-1 text-caption uppercase tracking-wide text-rui-text-secondary">
          {{ t('exchange_balances.refresh_menu.section') }}
        </div>
        <ExchangeRefreshMenuItem
          v-for="exchange in exchanges"
          :key="exchange"
          :exchange="exchange"
          @refresh="close(); emit('refresh-exchange', $event)"
        />
      </div>
    </template>
  </RefreshSplitButton>
</template>
