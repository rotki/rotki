<template>
  <table-expand-container
    :colspan="colspan - 1"
    :offset="1"
    :padded="false"
    visible
  >
    <template #append>
      <v-expansion-panels
        v-model="panel"
        :class="css['expansions-panels']"
        multiple
      >
        <v-expansion-panel>
          <v-expansion-panel-header
            v-if="transaction.ignoredInAccounting && events.length > 0"
          >
            <template #default="{ open }">
              <div class="primary--text font-weight-bold">
                {{
                  open
                    ? tc('transactions.events.view.hide')
                    : tc('transactions.events.view.show', 0, {
                        length: events.length
                      })
                }}
              </div>
            </template>
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <div
              class="my-n4"
              :class="{
                'pt-4': transaction.ignoredInAccounting && events.length > 0
              }"
            >
              <data-table
                :class="css.table"
                :headers="headers"
                :items="events"
                :no-data-text="tc('transactions.events.loading')"
                class="transparent"
                hide-default-footer
                :hide-default-header="$vuetify.breakpoint.mdAndUp"
              >
                <template #item.type="{ item }">
                  <transaction-event-type :event="item" />
                </template>
                <template #item.asset="{ item }">
                  <transaction-event-asset :event="item" />
                </template>
                <template #item.description="{ item }">
                  <transaction-event-note
                    :notes="item.notes"
                    :amount="item.balance.amount"
                    :asset="item.asset"
                  />
                </template>
                <template #item.actions="{ item }">
                  <row-actions
                    :delete-tooltip="tc('transactions.events.actions.delete')"
                    :edit-tooltip="tc('transactions.events.actions.edit')"
                    @edit-click="editEvent(item)"
                    @delete-click="deleteEvent(item)"
                  />
                </template>
              </data-table>
            </div>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </template>
  </table-expand-container>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import {
  EthTransactionEntry,
  EthTransactionEventEntry
} from '@/store/history/types';
import { transformEntryWithMeta } from '@/store/history/utils';
import { EthTransactionEventWithMeta } from '@/types/history/tx';

const TransactionEventNote = defineAsyncComponent(
  () => import('@/components/history/transactions/TransactionEventNote.vue')
);
const RowActions = defineAsyncComponent(
  () => import('@/components/helper/RowActions.vue')
);
const TransactionEventType = defineAsyncComponent(
  () => import('@/components/history/transactions/TransactionEventType.vue')
);
const TransactionEventAsset = defineAsyncComponent(
  () => import('@/components/history/transactions/TransactionEventAsset.vue')
);
const TableExpandContainer = defineAsyncComponent(
  () => import('@/components/helper/table/TableExpandContainer.vue')
);

const props = defineProps({
  transaction: {
    required: true,
    type: Object as PropType<EthTransactionEntry>
  },
  colspan: { required: true, type: Number }
});

const emit = defineEmits<{
  (e: 'edit:event', data: EthTransactionEventEntry): void;
  (
    e: 'delete:event',
    data: {
      tx: EthTransactionEntry;
      txEvent: EthTransactionEventEntry;
    }
  ): void;
}>();

const { transaction } = toRefs(props);

const css = useCssModule();
const { tc } = useI18n();

const headers: DataTableHeader[] = [
  {
    text: tc('common.type'),
    value: 'type',
    sortable: false,
    cellClass: css['row__type']
  },
  {
    text: tc('common.asset'),
    value: 'asset',
    sortable: false
  },
  {
    text: tc('transactions.events.headers.description'),
    value: 'description',
    sortable: false,
    cellClass: css['row__description']
  },
  {
    text: '',
    value: 'actions',
    align: 'end',
    sortable: false,
    cellClass: css['row__actions']
  }
];

const events = computed<EthTransactionEventEntry[]>(() => {
  return get(transaction).decodedEvents!.map(
    (event: EthTransactionEventWithMeta) => {
      return transformEntryWithMeta(event);
    }
  );
});

const editEvent = (item: EthTransactionEventEntry) => emit('edit:event', item);
const deleteEvent = (item: EthTransactionEventEntry) =>
  emit('delete:event', { txEvent: item, tx: get(transaction) });

const panel = ref<number[]>(get(transaction).ignoredInAccounting ? [] : [0]);

watch(transaction, (current, old) => {
  if (old.ignoredInAccounting && !current.ignoredInAccounting) {
    panel.value = [0];
  } else if (!old.ignoredInAccounting && current.ignoredInAccounting) {
    panel.value = [];
  }
});
</script>

<style lang="scss" module>
.table {
  :global {
    .v-data-table {
      &__wrapper {
        overflow-x: hidden;

        tbody {
          tr {
            &:hover {
              background-color: transparent !important;
            }

            td {
              padding-top: 1rem !important;
              padding-bottom: 1rem !important;

              @media screen and (max-width: 599px) {
                padding-left: 0 !important;
                padding-right: 0 !important;
              }
            }
          }
        }
      }
    }
  }
}

.row {
  &__type {
    width: 250px;
    padding-left: 0 !important;
  }

  &__description {
    width: 40%;
    min-width: 300px;
    line-height: 1.5rem;
    word-break: break-word;
  }

  &__actions {
    width: 1px;
    padding-right: 0 !important;
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
</style>
