<script setup lang="ts">
import type { AssetBalanceWithPriceAndChains } from '@rotki/common';
import type { BankBalanceData } from '@/modules/banks/use-bank-data';
import { useI18n } from 'vue-i18n';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import { bankAmountFormat } from '@/modules/banks/bank-balances';
import BankAccountsTable from '@/modules/banks/components/BankAccountsTable.vue';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';

const search = defineModel<string>('search', { required: true });

const { selectedBank, balances, loading = false, isBankLoading } = defineProps<{
  /** The bank the page shows; its accounts are listed instead of every bank's holdings. */
  selectedBank?: BankBalanceData;
  /** Every bank's holdings together, listed when no bank is selected. */
  balances: AssetBalanceWithPriceAndChains[];
  /** Whether every bank is being refreshed. */
  loading?: boolean;
  isBankLoading: (identifier: string) => boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <BankAccountsTable
    v-if="selectedBank && (selectedBank.accounts.length > 0 || isBankLoading(selectedBank.identifier))"
    :accounts="selectedBank.accounts"
    :search="search"
    :loading="isBankLoading(selectedBank.identifier) && selectedBank.accounts.length === 0"
  />
  <AssetBalances
    v-else-if="!selectedBank && (balances.length > 0 || loading)"
    v-model:search="search"
    data-testid="bank-asset-balances"
    :breakdown="{ hide: true }"
    :loading="loading && balances.length === 0"
    :balances="balances"
    :display="{ amountFormat: bankAmountFormat, stickyHeader: true }"
  />
  <TableEmptyNotice
    v-else
    icon="lu-landmark"
    :title="t('bank_balances.empty_table.title')"
    :description="t('bank_balances.empty_table.description')"
  />
</template>
