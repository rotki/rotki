<template>
  <table-expand-container
    visible
    :colspan="colspan - 2"
    :padded="false"
    :offset="2"
  >
    <template #append>
      <div class="my-n4">
        <data-table
          class="transparent"
          :class="$style.table"
          :headers="headers"
          :items="events"
          item-key="identifier"
          hide-default-footer
          hide-default-header
          :mobile-breakpoint="0"
        >
          <template #item.type="{ item }">
            <transaction-event-type-wrapper :event="item">
              <div class="grey--text">
                <hash-link :text="item.locationLabel" />
              </div>
            </transaction-event-type-wrapper>
          </template>
          <template #item.asset="{ item }">
            <transaction-event-asset :event="item" />
          </template>
          <template #item.description="{ item }">
            <template v-for="(note, index) in formatNotes(item.notes)">
              <span v-if="note.isAddress" :key="index" class="d-inline-flex">
                <hash-link
                  :class="$style.description__address"
                  :text="note.word"
                  :tx="note.isTransaction"
                />
              </span>
              <span v-else :key="index">
                {{ note.word }}
              </span>
            </template>
          </template>
        </data-table>
      </div>
    </template>
  </table-expand-container>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs,
  unref
} from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import TransactionEventAsset from '@/components/history/transactions/TransactionEventAsset.vue';
import TransactionEventTypeWrapper from '@/components/history/transactions/TransactionEventTypeWrapper.vue';
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
    TransactionEventTypeWrapper,
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
  setup(props) {
    const { transaction } = toRefs(props);

    // @ts-ignore
    const { $style } = useProxy();

    const headers: DataTableHeader[] = [
      {
        text: i18n.t('transactions.event_headers.type').toString(),
        value: 'type',
        sortable: false,
        cellClass: `${$style.type} pl-0`
      },
      {
        text: i18n.t('transactions.event_headers.asset').toString(),
        value: 'asset',
        sortable: false
      },
      {
        text: i18n.t('transactions.event_headers.description').toString(),
        value: 'description',
        sortable: false,
        width: '50%',
        cellClass: `${$style.description} pl-0`
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
      notes: string
    ): { word: string; isAddress: boolean; isTransaction: boolean }[] => {
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

    return {
      formatNotes,
      events,
      headers
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

.type {
  width: 250px;
}

.description {
  width: 50%;
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
</style>
