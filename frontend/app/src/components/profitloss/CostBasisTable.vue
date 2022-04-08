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
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.fullAmount="{ item }">
        <amount-display :value="item.event.fullAmount" />
      </template>
      <template #item.rate="{ item }">
        <amount-display :value="item.event.rate" />
      </template>
      <template #item.time="{ item }">
        <date-display :timestamp="item.event.timestamp" />
      </template>
      <template #item.taxable="{ item }">
        <v-icon v-if="item.taxable" color="success">mdi-check</v-icon>
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
    text: i18n.t('cost_basis_table.headers.amount').toString(),
    value: 'amount',
    align: 'end'
  },
  {
    text: i18n.t('cost_basis_table.headers.full_amount').toString(),
    value: 'fullAmount',
    align: 'end'
  },
  {
    text: i18n.t('cost_basis_table.headers.rate').toString(),
    value: 'rate',
    align: 'end'
  },
  {
    text: i18n.t('cost_basis_table.headers.time').toString(),
    value: 'time'
  },
  {
    text: i18n.t('cost_basis_table.headers.taxable').toString(),
    value: 'taxable'
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
