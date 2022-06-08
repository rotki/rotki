<template>
  <table-expand-container
    visible
    :colspan="colspan"
    :padded="false"
    :offset="1"
    :offset-class-name="$style.offset"
  >
    <template #offset>
      <div v-if="showGroupLine" :class="$style.group">
        <div :class="$style['group__line']" />
      </div>
    </template>
    <template #append>
      <v-expansion-panels
        v-model="panel"
        :class="$style['expansions-panels']"
        multiple
      >
        <v-expansion-panel>
          <v-expansion-panel-header>
            <template #default="{ open }">
              <div class="primary--text font-weight-bold">
                {{
                  open
                    ? $t('profit_loss_events.cost_basis.hide')
                    : $t('profit_loss_events.cost_basis.show')
                }}
              </div>
            </template>
          </v-expansion-panel-header>

          <v-expansion-panel-content>
            <card class="mt-4">
              <template #title>
                {{ $t('cost_basis_table.cost_basis') }}
                <span class="text-caption ml-2">
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
                  <amount-display
                    force-currency
                    :value="item.event.fullAmount"
                  />
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
            </card>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </template>
  </table-expand-container>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  Ref
} from '@vue/composition-api';
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
  name: 'CostBasisTable',
  components: { DataTable },
  props: {
    costBasis: { required: true, type: Object as PropType<CostBasis> },
    colspan: { required: true, type: Number },
    currency: { required: false, type: String, default: CURRENCY_USD },
    showGroupLine: { required: false, type: Boolean, default: false }
  },
  setup() {
    const { currencySymbol } = setupGeneralSettings();

    const panel = ref<number[]>([]);

    return {
      headers: getHeaders(currencySymbol),
      panel
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

.expansions {
  &-panels {
    :global {
      .v-expansion-panel {
        background: transparent !important;

        &::before {
          box-shadow: none;
        }

        &-header {
          padding: 0;
          min-height: auto;
          width: auto;
        }

        &-content {
          &__wrap {
            padding: 0;
          }
        }
      }
    }
  }
}

.offset {
  padding: 0 !important;
}

.group {
  height: 100%;
  position: relative;
  width: 10px;
  margin-left: 1.5rem;

  &__line {
    position: absolute;
    height: 100%;
    left: 50%;
    width: 0;
    transform: translateX(-50%);
    border-left: 2px dashed var(--v-primary-base);
  }
}
</style>
