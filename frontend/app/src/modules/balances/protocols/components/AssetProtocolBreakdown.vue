<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import { type ProtocolBalanceWithChains, transformCase } from '@rotki/common';
import { AssetAmountDisplay, FiatDisplay, ValueDisplay } from '@/modules/amount-display/components';
import ChainBalances from '@/modules/balances/protocols/components/ChainBalances.vue';
import ProtocolIcon from '@/modules/balances/protocols/ProtocolIcon.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

defineProps<{
  data: ProtocolBalanceWithChains[];
  asset?: string;
  loading?: boolean;
}>();

const sort = ref<DataTableSortData<ProtocolBalanceWithChains>>({
  column: 'value',
  direction: 'desc',
});

const { t } = useI18n({ useScope: 'global' });
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const cols = computed<DataTableColumn<ProtocolBalanceWithChains>[]>(() => [{
  align: 'start',
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
  class: 'text-no-wrap',
  key: 'value',
  label: t('common.value_in_symbol', {
    symbol: get(currencySymbol),
  }),
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
        <ProtocolIcon
          :protocol="transformCase(row.protocol)"
          :size="20"
        >
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
      </div>
      <ChainBalances
        v-if="row.protocol.toLowerCase() === 'address' && row.chains && Object.keys(row.chains).length > 0"
        class="ms-11 my-1"
        :chains="row.chains"
        :asset="asset"
        :loading="loading"
      />
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
