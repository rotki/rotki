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
        :class="$style['expansions-panels']"
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
                    ? $t('transactions.events.view.hide')
                    : $t('transactions.events.view.show', {
                        length: events.length
                      })
                }}
              </div>
            </template>
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <div class="my-n4">
              <data-table
                :class="$style.table"
                :headers="headers"
                :items="events"
                :mobile-breakpoint="0"
                :no-data-text="$t('transactions.events.loading')"
                class="transparent"
                hide-default-footer
                hide-default-header
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
                    :delete-tooltip="$t('transactions.events.actions.delete')"
                    :edit-tooltip="$t('transactions.events.actions.edit')"
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

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import RowActions from '@/components/helper/RowActions.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import TransactionEventAsset from '@/components/history/transactions/TransactionEventAsset.vue';
import TransactionEventNote from '@/components/history/transactions/TransactionEventNote.vue';
import TransactionEventType from '@/components/history/transactions/TransactionEventType.vue';
import { useProxy } from '@/composables/common';
import i18n from '@/i18n';
import { EthTransactionEventWithMeta } from '@/services/history/types';
import {
  EthTransactionEntry,
  EthTransactionEventEntry
} from '@/store/history/types';
import { transformEntryWithMeta } from '@/store/history/utils';

export default defineComponent({
  name: 'TransactionEvents',
  components: {
    TransactionEventNote,
    RowActions,
    TransactionEventType,
    TransactionEventAsset,
    TableExpandContainer
  },
  props: {
    transaction: {
      required: true,
      type: Object as PropType<EthTransactionEntry>
    },
    colspan: { required: true, type: Number }
  },
  emits: ['edit:event', 'delete:event'],
  setup(props, { emit }) {
    const { transaction } = toRefs(props);

    // @ts-ignore
    const { $style } = useProxy();

    const headers: DataTableHeader[] = [
      {
        text: i18n.t('transactions.events.headers.type').toString(),
        value: 'type',
        sortable: false,
        cellClass: $style['row__type']
      },
      {
        text: i18n.t('transactions.events.headers.asset').toString(),
        value: 'asset',
        sortable: false
      },
      {
        text: i18n.t('transactions.events.headers.description').toString(),
        value: 'description',
        sortable: false,
        cellClass: $style['row__description']
      },
      {
        text: '',
        value: 'actions',
        align: 'end',
        sortable: false,
        cellClass: $style['row__actions']
      }
    ];

    const events = computed<EthTransactionEventEntry[]>(() => {
      return get(transaction).decodedEvents!.map(
        (event: EthTransactionEventWithMeta) => {
          return transformEntryWithMeta(event);
        }
      );
    });

    const editEvent = (item: EthTransactionEventEntry) =>
      emit('edit:event', item);
    const deleteEvent = (item: EthTransactionEventEntry) =>
      emit('delete:event', item);

    const panel = ref<number[]>(
      get(transaction).ignoredInAccounting ? [] : [0]
    );

    watch(transaction, (current, old) => {
      if (old.ignoredInAccounting && !current.ignoredInAccounting) {
        panel.value = [0];
      } else if (!old.ignoredInAccounting && current.ignoredInAccounting) {
        panel.value = [];
      }
    });

    return {
      panel,
      events,
      headers,
      editEvent,
      deleteEvent
    };
  }
});
</script>

<style lang="scss" module>
.table {
  :global {
    tbody {
      tr {
        &:hover {
          background-color: transparent !important;
        }

        td {
          padding-top: 1rem !important;
          padding-bottom: 1rem !important;
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
