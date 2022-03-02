<template>
  <table-expand-container
    visible
    :colspan="colspan - 1"
    :padded="false"
    :offset="1"
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
                class="transparent"
                :class="$style.table"
                :headers="headers"
                :items="events"
                item-key="identifier"
                hide-default-footer
                hide-default-header
                :no-data-text="$t('transactions.events.loading')"
                :mobile-breakpoint="0"
              >
                <template #item.type="{ item }">
                  <transaction-event-type :event="item" />
                </template>
                <template #item.asset="{ item }">
                  <transaction-event-asset :event="item" />
                </template>
                <template #item.description="{ item }">
                  <template v-for="(note, index) in formatNotes(item.notes)">
                    <span
                      v-if="note.isAddress"
                      :key="index"
                      class="d-inline-flex"
                    >
                      <hash-link
                        :class="$style['row__description__address']"
                        :text="note.word"
                        :tx="note.isTransaction"
                      />
                    </span>
                    <span v-else :key="index">
                      {{ note.word }}
                    </span>
                  </template>
                </template>
                <template #item.actions="{ item }">
                  <row-actions
                    :edit-tooltip="$t('transactions.events.actions.edit')"
                    :delete-tooltip="$t('transactions.events.actions.delete')"
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
  unref,
  watch
} from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import RowActions from '@/components/helper/RowActions.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import TransactionEventAsset from '@/components/history/transactions/TransactionEventAsset.vue';
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
      return unref(transaction).decodedEvents!.map(
        (event: EthTransactionEventWithMeta) => {
          return transformEntryWithMeta(event);
        }
      );
    });

    const formatNotes = (
      notes: string | null
    ): { word: string; isAddress: boolean; isTransaction: boolean }[] => {
      if (!notes) return [];

      // label each word from notes whether it is an address or not
      const words = notes.split(' ');

      return words.map((word, index) => {
        const isAddress = word.startsWith('0x') && word.length >= 42;
        const isTransaction =
          isAddress && index !== 0 && words[index - 1] === 'transaction';
        return {
          word,
          isAddress,
          isTransaction
        };
      });
    };

    const editEvent = (item: EthTransactionEventEntry) =>
      emit('edit:event', item);
    const deleteEvent = (item: EthTransactionEventEntry) =>
      emit('delete:event', item);

    const panel = ref<number[]>(
      unref(transaction).ignoredInAccounting ? [] : [0]
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
      formatNotes,
      events,
      headers,
      editEvent,
      deleteEvent
    };
  }
});
</script>

<style module lang="scss">
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

    &__address {
      background: var(--v-rotki-light-grey-darken1);
      padding: 0 4px 0 8px;
      border-radius: 50px;
      margin: 2px;
    }
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
