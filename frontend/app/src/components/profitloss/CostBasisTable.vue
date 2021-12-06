<template>
  <table-expand-container :visible="visible" :colspan="colspan" :padded="false">
    <template #title>
      {{ $t('cost_basis_table.cost_basis') }}
      <span class="text-caption">
        {{
          costBasis.isComplete
            ? $t('cost_basis_table.complete')
            : $t('cost_basis_table.incomplete')
        }}
      </span>
    </template>
    <data-table
      :class="$style.table"
      :items="costBasis.matchedAcquisitions"
      :headers="headers"
      item-key="id"
      sort-by="time"
    >
      <template #item.location="{ item }">
        <location-display :identifier="item.location" />
      </template>
      <template #item.usedAmount="{ item }">
        <amount-display :value="item.usedAmount" />
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.fee="{ item }">
        <amount-display :value="item.fee" />
      </template>
      <template #item.feeRate="{ item }">
        <amount-display :value="item.feeRate" />
      </template>
      <template #item.time="{ item }">
        <date-display :timestamp="item.time" />
      </template>
    </data-table>
  </table-expand-container>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import DataTable from '@/components/helper/DataTable.vue';
import i18n from '@/i18n';
import { CostBasis } from '@/types/reports';

const getHeaders: () => DataTableHeader[] = () => [
  {
    text: i18n.t('cost_basis_table.headers.location').toString(),
    value: 'location',
    width: '120px',
    align: 'center'
  },
  {
    text: i18n.t('cost_basis_table.headers.description').toString(),
    value: 'description'
  },
  {
    text: i18n.t('cost_basis_table.headers.used_amount').toString(),
    value: 'usedAmount',
    align: 'end'
  },
  {
    text: i18n.t('cost_basis_table.headers.amount').toString(),
    value: 'amount',
    align: 'end'
  },
  {
    text: i18n.t('cost_basis_table.headers.rate').toString(),
    value: 'rate',
    align: 'end'
  },
  {
    text: i18n.t('cost_basis_table.headers.fee_rate').toString(),
    value: 'feeRate',
    align: 'end'
  },
  {
    text: i18n.t('cost_basis_table.headers.time').toString(),
    value: 'time'
  }
];

export default defineComponent({
  name: 'CostBasicTable',
  components: { DataTable },
  props: {
    costBasis: { required: true, type: Object as PropType<CostBasis> },
    visible: { required: true, type: Boolean },
    colspan: { required: true, type: Number }
  },
  setup() {
    return {
      headers: getHeaders()
    };
  }
});
</script>

<style module lang="scss">
.table {
  :global {
    th {
      &:first-child {
        span {
          padding-left: 16px;
        }
      }
    }
  }
}
</style>
