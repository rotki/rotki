<script setup lang="ts">
import type { ProtocolBalance } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import ProtocolIcon from '@/modules/balances/protocols/ProtocolIcon.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

defineProps<{
  data: ProtocolBalance[];
  asset?: string;
  loading?: boolean;
}>();

const sort = ref<DataTableSortData<ProtocolBalance>>({
  column: 'usdValue',
  direction: 'desc',
});

const { t } = useI18n({ useScope: 'global' });
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const cols = computed<DataTableColumn<ProtocolBalance>[]>(() => [{
  align: 'start',
  key: 'protocol',
  label: t('common.protocol'),
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
  key: 'usdValue',
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
          :protocol="row.protocol"
          :loading="loading"
        >
          <template #default="{ protocol }">
            <span class="font-medium">
              {{ protocol }}
            </span>
          </template>
        </ProtocolIcon>
      </div>
    </template>

    <template #item.amount="{ row }">
      <AmountDisplay
        :value="row.amount"
        :asset="asset"
        :asset-padding="0.1"
      />
    </template>

    <template #item.usdValue="{ row }">
      <AmountDisplay
        :asset-padding="0.1"
        fiat-currency="USD"
        :value="row.usdValue"
        show-currency="symbol"
      />
    </template>
  </RuiDataTable>
</template>
