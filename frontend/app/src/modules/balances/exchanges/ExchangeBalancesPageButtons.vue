<script setup lang="ts">
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import ExchangeBalancesRefreshButton from '@/modules/balances/exchanges/ExchangeBalancesRefreshButton.vue';
import HideSmallBalances from '@/modules/settings/HideSmallBalances.vue';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

const { exchanges, selected, loading = false } = defineProps<{
  exchanges: string[];
  /** The exchange the page shows; refresh then targets only it. */
  selected?: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'refresh': [];
  'refresh-all': [];
  'refresh-exchange': [exchange: string];
  'add': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ExchangeBalancesRefreshButton
    :exchanges="exchanges"
    :selected="selected"
    :loading="loading"
    @refresh="emit('refresh')"
    @refresh-all="emit('refresh-all')"
    @refresh-exchange="emit('refresh-exchange', $event)"
  />
  <RuiButton
    color="primary"
    data-testid="add-exchange"
    @click="emit('add')"
  >
    <template #prepend>
      <RuiIcon name="lu-plus" />
    </template>
    {{ t('exchange_balances.add_exchange') }}
  </RuiButton>
  <HideSmallBalances :source="BalanceSource.EXCHANGES" />
</template>
