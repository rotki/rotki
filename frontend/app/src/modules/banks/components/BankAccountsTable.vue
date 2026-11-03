<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { BankAccountBalance } from '@/modules/banks/types';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { bankAmountFormat } from '@/modules/banks/bank-balances';
import { useBankAccountLabel } from '@/modules/banks/use-bank-account-label';

const { accounts, search = '', loading = false } = defineProps<{
  /** The accounts of one bank, each holding a single currency. */
  accounts: BankAccountBalance[];
  /** Narrows the accounts to those whose name, IBAN or currency contains it. */
  search?: string;
  loading?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { accountLabel } = useBankAccountLabel();

const sort = ref<DataTableSortData<BankAccountBalance>>({ column: 'value', direction: 'desc' });

const cols = computed<DataTableColumn<BankAccountBalance>[]>(() => [{
  cellClass: 'py-2',
  key: 'name',
  label: t('bank_balances.accounts.account'),
  sortable: true,
}, {
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, {
  align: 'end',
  key: 'amount',
  label: t('common.amount'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'font-medium',
  key: 'value',
  label: t('common.value'),
  sortable: true,
}]);

const rows = computed<BankAccountBalance[]>(() => {
  const needle = search.trim().toLowerCase().replaceAll(/\s/g, '');
  if (needle === '')
    return accounts;
  return accounts.filter(({ asset, iban, name }) =>
    [name, iban ?? '', asset].some(field => field.toLowerCase().replaceAll(/\s/g, '').includes(needle)));
});
</script>

<template>
  <RuiDataTable
    v-model:sort="sort"
    :cols="cols"
    :rows="rows"
    :loading="loading"
    :empty="{ description: t('data_table.no_data') }"
    row-attr="identifier"
    dense
    outlined
    data-testid="bank-accounts"
  >
    <template #item.name="{ row }">
      <div
        class="flex flex-col min-w-0"
        data-testid="bank-account"
        :data-account="row.identifier"
      >
        <span class="font-medium truncate">{{ accountLabel(row).title }}</span>
        <span
          v-if="accountLabel(row).subtitle"
          class="text-caption text-rui-text-secondary font-mono truncate"
          data-testid="bank-account-iban"
        >
          {{ accountLabel(row).subtitle }}
        </span>
      </div>
    </template>
    <template #item.asset="{ row }">
      <AssetDetails
        :asset="row.asset"
        :display="{ dense: true, inline: true, size: '24px' }"
      />
    </template>
    <template #item.amount="{ row }">
      <ValueDisplay
        :value="row.amount"
        :format="bankAmountFormat(row.asset)"
      />
    </template>
    <template #item.value="{ row }">
      <FiatDisplay :value="row.value" />
    </template>
  </RuiDataTable>
</template>
