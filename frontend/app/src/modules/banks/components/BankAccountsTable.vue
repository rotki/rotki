<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { AssetActions, AssetDisplay } from '@/modules/assets/types';
import type { BankAccountBalance } from '@/modules/banks/types';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { bankAmountFormat } from '@/modules/banks/bank-balances';
import { type BankAccountLabel, useBankAccountLabel } from '@/modules/banks/use-bank-account-label';

const { accounts, search = '', loading = false } = defineProps<{
  /** The accounts of one bank, each holding a single currency. */
  accounts: BankAccountBalance[];
  /** Narrows the accounts to those whose name, IBAN or currency contains it. */
  search?: string;
  loading?: boolean;
}>();

/** The currency icon beside each account: decoration, so it carries no asset menu. */
const ICON_DISPLAY: AssetDisplay = { iconOnly: true, size: '28px' };
const ICON_ACTIONS: AssetActions = { hideMenu: true };

const { t } = useI18n({ useScope: 'global' });
const { accountLabel } = useBankAccountLabel();

const sort = ref<DataTableSortData<BankAccountBalance>>({ column: 'value', direction: 'desc' });

const cols = computed<DataTableColumn<BankAccountBalance>[]>(() => [{
  cellClass: 'h-15',
  key: 'name',
  label: t('bank_balances.accounts.account'),
  sortable: true,
}, {
  align: 'end',
  key: 'amount',
  label: t('common.balance'),
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

const labels = computed<Map<string, BankAccountLabel>>(() => new Map(accounts.map(account => [account.identifier, accountLabel(account)])));

function labelOf(account: BankAccountBalance): BankAccountLabel {
  return get(labels).get(account.identifier) ?? accountLabel(account);
}
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
        class="flex items-center gap-3"
        data-testid="bank-account"
        :data-account="row.identifier"
      >
        <AssetDetails
          :asset="row.asset"
          :display="ICON_DISPLAY"
          :actions="ICON_ACTIONS"
          class="shrink-0"
        />
        <div class="flex flex-col min-w-0 gap-0.5">
          <span
            class="text-body-2 font-medium truncate"
            data-testid="bank-account-name"
          >
            {{ labelOf(row).title }}
          </span>
          <span
            v-if="labelOf(row).subtitle"
            class="text-xs text-rui-text-secondary tabular-nums tracking-wide truncate"
            data-testid="bank-account-iban"
          >
            {{ labelOf(row).subtitle }}
          </span>
        </div>
      </div>
    </template>
    <template #item.amount="{ row }">
      <AssetAmountDisplay
        :asset="row.asset"
        :amount="row.amount"
        no-collection-parent
        :decimals="bankAmountFormat(row.asset).decimals"
        class="tabular-nums"
      />
    </template>
    <template #item.value="{ row }">
      <FiatDisplay
        :value="row.value"
        class="tabular-nums"
      />
    </template>
  </RuiDataTable>
</template>
