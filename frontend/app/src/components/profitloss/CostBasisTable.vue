<template>
  <table-expand-container
    visible
    :colspan="colspan"
    :padded="false"
    :offset="1"
    :offset-class-name="css.offset"
  >
    <template #offset>
      <div v-if="showGroupLine" :class="css.group">
        <div :class="css['group__line']" />
      </div>
    </template>
    <template #append>
      <v-expansion-panels
        v-model="panel"
        :class="css['expansions-panels']"
        multiple
      >
        <v-expansion-panel>
          <v-expansion-panel-header>
            <template #default="{ open }">
              <div class="primary--text font-weight-bold">
                {{
                  open
                    ? tc('profit_loss_events.cost_basis.hide')
                    : tc('profit_loss_events.cost_basis.show')
                }}
              </div>
            </template>
          </v-expansion-panel-header>

          <v-expansion-panel-content>
            <card class="mt-4">
              <template #title>
                {{ tc('cost_basis_table.cost_basis') }}
                <span class="text-caption ml-2">
                  {{
                    costBasis.isComplete
                      ? tc('cost_basis_table.complete')
                      : tc('cost_basis_table.incomplete')
                  }}
                </span>
              </template>
              <data-table
                :class="css.table"
                :items="matchedAcquisitions"
                :headers="tableHeaders"
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

<script setup lang="ts">
import { PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import DataTable from '@/components/helper/DataTable.vue';
import { CostBasis } from '@/types/reports';

const props = defineProps({
  costBasis: { required: true, type: Object as PropType<CostBasis> },
  colspan: { required: true, type: Number },
  currency: {
    required: false,
    type: String as PropType<string | null>,
    default: null
  },
  showGroupLine: { required: false, type: Boolean, default: false }
});

const { costBasis, currency } = toRefs(props);

const panel = ref<number[]>([]);
const { tc } = useI18n();

const css = useCssModule();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: tc('cost_basis_table.headers.amount'),
    value: 'amount',
    align: 'end'
  },
  {
    text: tc('cost_basis_table.headers.full_amount'),
    value: 'fullAmount',
    align: 'end'
  },
  {
    text: tc('cost_basis_table.headers.remaining_amount'),
    value: 'remainingAmount',
    align: 'end'
  },
  {
    text: tc('cost_basis_table.headers.rate', 0, {
      currency: get(currency)
    }),
    value: 'rate',
    align: 'end'
  },
  {
    text: tc('common.datetime'),
    value: 'time'
  },
  {
    text: tc('cost_basis_table.headers.taxable'),
    value: 'taxable'
  }
]);

const matchedAcquisitions = computed(() => {
  return get(costBasis).matchedAcquisitions ?? [];
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
