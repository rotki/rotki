<script setup lang="ts">
import type { BankConnectionIdentity } from '@/modules/banks/types';
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import BankBalancesRefreshButton from '@/modules/banks/components/BankBalancesRefreshButton.vue';

const { banks, selected, loading = false, isBankLoading, connected = false, canAdd = false } = defineProps<{
  banks: BankConnectionIdentity[];
  /** The bank the page shows; refresh then targets only it. */
  selected?: string;
  /** Whether every bank is being refreshed. */
  loading?: boolean;
  isBankLoading: (identifier: string) => boolean;
  /** Whether any bank is connected; the refresh button shows only then. */
  connected?: boolean;
  /** Whether a bank connector is available to add a connection with. */
  canAdd?: boolean;
}>();

const emit = defineEmits<{
  'refresh': [];
  'refresh-all': [];
  'refresh-bank': [bank: BankConnectionIdentity];
  'add': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <BankBalancesRefreshButton
    v-if="connected"
    :banks="banks"
    :selected="selected"
    :loading="loading"
    :is-bank-loading="isBankLoading"
    @refresh="emit('refresh')"
    @refresh-all="emit('refresh-all')"
    @refresh-bank="emit('refresh-bank', $event)"
  />
  <RuiButton
    color="primary"
    data-testid="add-bank-connection"
    :disabled="!canAdd"
    @click="emit('add')"
  >
    <template #prepend>
      <RuiIcon name="lu-plus" />
    </template>
    {{ t('bank_balances.add_bank') }}
  </RuiButton>
</template>
