<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { SolanaStakeAccountRow } from '@/modules/staking/solana/use-solana-stake-accounts';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { SOL_IDENTIFIER, SOLANA_LOCATION } from '@/modules/staking/solana/constants';

const { rows, loaded, loading } = defineProps<{
  rows: SolanaStakeAccountRow[];
  /** Whether a query has succeeded; until then an empty table says nothing could be loaded. */
  loaded: boolean;
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const columns = computed<DataTableColumn<SolanaStakeAccountRow>[]>(() => [{
  key: 'address',
  label: t('staking_page.solana.table.stake_account'),
}, {
  key: 'owner',
  label: t('staking_page.solana.table.owner'),
}, {
  key: 'validator',
  label: t('staking_page.solana.table.validator'),
}, {
  align: 'end',
  key: 'amount',
  label: t('staking_page.solana.table.amount'),
}]);
</script>

<template>
  <RuiDataTable
    dense
    outlined
    hide-default-footer
    row-attr="address"
    data-testid="solana-stake-accounts"
    :cols="columns"
    :rows="rows"
    :loading="loading"
    :empty="{ label: loaded ? t('staking_page.solana.table.empty') : t('staking_page.not_loaded') }"
  >
    <template #item.address="{ row }">
      <HashLink
        :text="row.address"
        :location="SOLANA_LOCATION"
      />
    </template>
    <template #item.owner="{ row }">
      <HashLink
        :text="row.owner"
        :location="SOLANA_LOCATION"
      />
    </template>
    <template #item.validator="{ row }">
      <HashLink
        v-if="row.validator"
        :text="row.validator"
        :location="SOLANA_LOCATION"
      />
      <span
        v-else
        class="text-rui-text-secondary"
      >
        {{ t('staking_page.solana.table.not_delegated') }}
      </span>
    </template>
    <template #item.amount="{ row }">
      <BalanceDisplay
        :asset="SOL_IDENTIFIER"
        :value="{ amount: row.amount }"
        calculate-value
      />
    </template>
  </RuiDataTable>
</template>
