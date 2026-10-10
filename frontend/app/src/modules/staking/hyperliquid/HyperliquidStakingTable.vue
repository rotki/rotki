<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { HyperliquidStakingRow } from '@/modules/staking/hyperliquid/use-hyperliquid-staking';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { HYPE_IDENTIFIER, HYPERLIQUID_LOCATION } from '@/modules/staking/hyperliquid/constants';

const { rows, loading } = defineProps<{
  rows: HyperliquidStakingRow[];
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const columns = computed<DataTableColumn<HyperliquidStakingRow>[]>(() => [{
  key: 'address',
  label: t('staking_page.hyperliquid.table.address'),
}, {
  align: 'end',
  key: 'delegated',
  label: t('staking_page.hyperliquid.table.delegated'),
}, {
  align: 'end',
  key: 'undelegated',
  label: t('staking_page.hyperliquid.table.undelegated'),
}, {
  align: 'end',
  key: 'pendingWithdrawal',
  label: t('staking_page.hyperliquid.table.pending_withdrawal'),
}]);
</script>

<template>
  <RuiDataTable
    dense
    outlined
    row-attr="address"
    data-testid="hyperliquid-staking-accounts"
    :cols="columns"
    :rows="rows"
    :loading="loading"
    :empty="{ label: t('staking_page.hyperliquid.table.empty') }"
  >
    <template #item.address="{ row }">
      <HashLink
        :text="row.address"
        :location="HYPERLIQUID_LOCATION"
      />
    </template>
    <template #item.delegated="{ row }">
      <BalanceDisplay
        :asset="HYPE_IDENTIFIER"
        :value="{ amount: row.delegated }"
        calculate-value
      />
    </template>
    <template #item.undelegated="{ row }">
      <BalanceDisplay
        :asset="HYPE_IDENTIFIER"
        :value="{ amount: row.undelegated }"
        calculate-value
      />
    </template>
    <template #item.pendingWithdrawal="{ row }">
      <BalanceDisplay
        :asset="HYPE_IDENTIFIER"
        :value="{ amount: row.pendingWithdrawal }"
        calculate-value
      />
    </template>
  </RuiDataTable>
</template>
