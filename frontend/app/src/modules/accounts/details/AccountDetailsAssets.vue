<script setup lang="ts">
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import AccountAssetBalances from '@/modules/accounts/balances/AccountAssetBalances.vue';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { sum } from '@/modules/core/common/display/balances';
import TableSearchField from '@/modules/core/table/TableSearchField.vue';

const selected = defineModel<string[] | undefined>('selected', { required: true });

const { chains, groupId, limit, searchable = false, selectionMode = false } = defineProps<{
  groupId: string;
  chains: string[];
  selectionMode?: boolean;
  /** Puts a search over the assets, for the tab that lists all of them at once. */
  searchable?: boolean;
  /** Shows only this many assets, the most valuable, until the rest are asked for. */
  limit?: number;
}>();

defineSlots<{
  /** Above the list, handed the value of every asset in scope, shown or not. */
  header?: (props: { value: BigNumber }) => any;
}>();

const search = ref<string>('');
const showAll = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });

const { useBlockchainBalances } = useAggregatedBalances();

const assets = useBlockchainBalances(() => chains, () => groupId);
const liabilities = useBlockchainBalances(() => chains, () => groupId, 'liabilities');

const capped = computed<boolean>(() => limit !== undefined && get(assets).length > limit);

const shownAssets = computed<AssetBalanceWithPrice[]>(() => {
  const all = get(assets);
  if (!get(capped) || get(showAll))
    return all;

  return [...all].sort((a: AssetBalanceWithPrice, b: AssetBalanceWithPrice): number => sortDesc(a.value, b.value)).slice(0, limit);
});

const value = computed<BigNumber>(() => sum(get(assets)));
</script>

<template>
  <div class="flex flex-col gap-2">
    <slot
      name="header"
      :value="value"
    />
    <div class="flex flex-col gap-4">
      <div
        v-if="searchable"
        class="flex"
      >
        <TableSearchField
          v-model="search"
          data-testid="account-details-assets-search"
        />
      </div>
      <AssetBalances
        v-model:search="search"
        v-model:selected="selected"
        :balances="shownAssets"
        show-per-protocol
        layout="panel"
        :selection-mode="selectionMode"
        :breakdown="{ scope: { chains, groupId } }"
        data-testid="account-details-assets"
      />
      <RuiButton
        v-if="capped"
        variant="text"
        color="primary"
        size="sm"
        class="self-start"
        data-testid="account-details-assets-show-all"
        @click="showAll = !showAll"
      >
        {{ showAll ? t('account_balances.show_top_assets', { count: limit }) : t('account_balances.show_all_assets', { count: assets.length }) }}
      </RuiButton>
      <AccountAssetBalances
        v-if="liabilities.length > 0"
        v-model:selected="selected"
        :title="t('account_balance_table.liabilities')"
        :assets="liabilities"
        :selection-mode="selectionMode"
        data-testid="account-details-liabilities"
      />
    </div>
  </div>
</template>
