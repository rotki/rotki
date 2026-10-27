<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import { type ProtocolBalanceWithChains, transformCase } from '@rotki/common';
import { AssetAmountDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import ChainBalances from '@/modules/balances/protocols/components/ChainBalances.vue';
import ProtocolIcon from '@/modules/balances/protocols/ProtocolIcon.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

defineProps<{
  data: ProtocolBalanceWithChains[];
  asset?: string;
  loading?: boolean;
}>();

const claimPages = new Map<string, string>([
  ['lido', 'https://stake.lido.fi/withdrawals/claim'],
  ['venice', 'https://venice.ai/token'],
]);

const sort = ref<DataTableSortData<ProtocolBalanceWithChains>>({
  column: 'value',
  direction: 'desc',
});

const { t } = useI18n({ useScope: 'global' });

const cols = computed<DataTableColumn<ProtocolBalanceWithChains>[]>(() => [{
  align: 'start',
  class: 'text-no-wrap w-full',
  key: 'protocol',
  label: t('common.location'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'py-0',
  class: 'text-no-wrap',
  key: 'amount',
  label: t('common.amount'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'font-medium',
  class: 'text-no-wrap',
  key: 'value',
  label: t('common.value'),
  sortable: true,
}]);
</script>

<template>
  <RuiDataTable
    v-model:sort="sort"
    :rows="data"
    :cols="cols"
    row-attr="protocol"
    :loading="loading"
    dense
    outlined
    class="asset-protocol-breakdown"
  >
    <template #item.protocol="{ row }">
      <div class="flex items-center gap-3">
        <ProtocolIcon :protocol="transformCase(row.protocol)">
          <template #default="{ protocol }">
            <div class="flex items-center gap-2">
              <div class="font-medium">
                <template v-if="protocol.toLowerCase() === 'address'">
                  {{ t('common.blockchain') }}
                </template>
                <template v-else>
                  {{ protocol }}
                </template>
              </div>
            </div>
          </template>
        </ProtocolIcon>
        <span
          v-if="row.awaitingClaim?.gt(0)"
          class="text-rui-warning text-xs"
        >
          {{ t('common.awaiting_claim') }}
          <AssetAmountDisplay
            v-if="asset"
            :asset="asset"
            :amount="row.awaitingClaim"
          />
        </span>
        <ExternalLink
          v-if="row.awaitingClaim?.gt(0) && claimPages.has(row.protocol)"
          :url="claimPages.get(row.protocol)"
          data-testid="asset-protocol-claim-link"
          class="text-xs"
        >
          {{ t('common.claim_page') }}
        </ExternalLink>
        <div
          v-if="row.awaitingClaim?.gt(0) && row.awaitingClaimAccounts?.length"
          class="flex flex-wrap items-center gap-1 text-xs"
          data-testid="asset-protocol-claim-accounts"
        >
          <span class="text-rui-text-secondary">{{ t('common.claim_with') }}</span>
          <HashLink
            v-for="account in row.awaitingClaimAccounts"
            :key="`${account.chain}-${account.address}`"
            :text="account.address"
            :location="account.chain"
          />
        </div>
        <ChainBalances
          v-if="row.protocol.toLowerCase() === 'address' && row.chains && Object.keys(row.chains).length > 0"
          :chains="row.chains"
          :asset="asset"
        />
      </div>
    </template>

    <template #item.amount="{ row }">
      <AssetAmountDisplay
        v-if="asset"
        :asset="asset"
        :amount="row.amount"
      />
      <ValueDisplay
        v-else
        :value="row.amount"
      />
    </template>

    <template #item.value="{ row }">
      <FiatDisplay :value="row.value" />
    </template>
  </RuiDataTable>
</template>
