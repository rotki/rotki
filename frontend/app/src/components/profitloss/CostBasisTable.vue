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
        <amount-display force-currency :value="item.amount" />
      </template>
      <template #item.fullAmount="{ item }">
        <amount-display force-currency :value="item.event.fullAmount" />
      </template>
      <template #item.remainingAmount="{ item }">
        <amount-display
          force-currency
          :value="item.event.fullAmount.minus(item.amount)"
        />
      </template>
      <template #item.rate="{ item }">
        <amount-display
          force-currency
          :value="item.event.rate"
          :fiat-currency="currency"
        />
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
import { computed, defineComponent, PropType, Ref } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import DataTable from '@/components/helper/DataTable.vue';
import { setupGeneralSettings } from '@/composables/session';
import { CURRENCY_USD } from '@/data/currencies';
import i18n from '@/i18n';
import { CostBasis } from '@/types/reports';

const getHeaders = (currency: Ref<string>) =>
  computed<DataTableHeader[]>(() => {
    return [
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
        text: i18n.t('cost_basis_table.headers.remaining_amount').toString(),
        value: 'remainingAmount',
        align: 'end'
      },
      {
        text: i18n
          .t('cost_basis_table.headers.rate', { currency: get(currency) })
          .toString(),
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
  });

export default defineComponent({
  name: 'CostBasicTable',
  components: { DataTable },
  props: {
    costBasis: { required: true, type: Object as PropType<CostBasis> },
    visible: { required: true, type: Boolean },
    colspan: { required: true, type: Number },
    currency: { required: false, type: String, default: CURRENCY_USD }
  },
  setup() {
    const { currencySymbol } = setupGeneralSettings();

    return {
      headers: getHeaders(currencySymbol)
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
