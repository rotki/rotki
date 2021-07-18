<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('transactions.loading') }}
    </template>
    {{ $t('transactions.loading_subtitle') }}
  </progress-screen>
  <v-container v-else>
    <blockchain-account-selector v-model="account" hint :chains="['ETH']" />
    <v-card class="mt-8">
      <v-card-title>
        <refresh-button
          :loading="refreshing"
          :tooltip="$t('transactions.refresh_tooltip')"
          @refresh="refresh"
        />
        <card-title class="ms-2">{{ $t('transactions.title') }}</card-title>
      </v-card-title>
      <v-card-text>
        <ignore-buttons
          :disabled="selected.length === 0 || loading || refreshing"
          @ignore="ignoreTransactions"
        />
        <v-sheet outlined rounded>
          <data-table
            :headers="headers"
            :items="visibleTransactions"
            show-expand
            single-expand
            :expanded="expanded"
            item-key="key"
            sort-by="timestamp"
            :page.sync="page"
            :loading="refreshing"
          >
            <template #header.selection>
              <v-simple-checkbox
                :ripple="false"
                :value="allSelected"
                color="primary"
                @input="setSelected($event)"
              />
            </template>
            <template #item.selection="{ item }">
              <v-simple-checkbox
                :ripple="false"
                color="primary"
                :value="selected.includes(getKey(item))"
                @input="selectionChanged(getKey(item), $event)"
              />
            </template>
            <template #item.ignoredInAccounting="{ item }">
              <v-icon v-if="item.ignoredInAccounting">mdi-check</v-icon>
            </template>
            <template #item.txHash="{ item }">
              <hash-link :text="item.txHash" tx />
              <v-chip
                v-if="item.gasPrice.lt(0)"
                small
                text-color="white"
                color="accent"
                class="mb-1 mt-1"
              >
                {{ $t('transaction_details.internal_transaction') }}
              </v-chip>
            </template>
            <template #item.fromAddress="{ item }">
              <hash-link :text="item.fromAddress" />
            </template>
            <template #item.toAddress="{ item }">
              <hash-link v-if="item.toAddress" :text="item.toAddress" />
              <span v-else>-</span>
            </template>
            <template #item.timestamp="{ item }">
              <date-display :timestamp="item.timestamp" />
            </template>
            <template #item.value="{ item }">
              <amount-display :value="toEth(item.value)" asset="ETH" />
            </template>
            <template #item.gasFee="{ item }">
              <amount-display :value="item.gasFee" asset="ETH" />
            </template>
            <template
              v-if="
                transactionsLimit <= transactionsTotal && transactionsLimit > 0
              "
              #body.append="{ headers }"
            >
              <upgrade-row
                :total="transactionsTotal"
                :limit="transactionsLimit"
                :colspan="headers.length"
                :label="$t('transactions.label')"
              />
            </template>
            <template #expanded-item="{ headers, item }">
              <transaction-details
                :transaction="item"
                :colspan="headers.length"
              />
            </template>
          </data-table>
        </v-sheet>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import { Component, Mixins, Watch } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters, mapMutations } from 'vuex';
import DateDisplay from '@/components/display/DateDisplay.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import DataTable from '@/components/helper/DataTable.vue';
import HashLink from '@/components/helper/HashLink.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import TransactionDetails from '@/components/history/TransactionsDetails.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import {
  FETCH_FROM_CACHE,
  FETCH_FROM_SOURCE,
  FETCH_REFRESH,
  HistoryActions,
  IGNORE_TRANSACTIONS
} from '@/store/history/consts';
import {
  EthTransactionWithFee,
  FetchSource,
  IgnoreActionPayload
} from '@/store/history/types';
import { ActionStatus, Message } from '@/store/types';
import { GeneralAccount } from '@/typing/types';
import { toUnit, Unit } from '@/utils/calculation';

@Component({
  components: {
    DataTable,
    CardTitle,
    IgnoreButtons,
    BlockchainAccountSelector,
    TransactionDetails,
    UpgradeRow,
    DateDisplay,
    HashLink,
    RefreshButton,
    ProgressScreen
  },
  computed: {
    ...mapGetters('history', [
      'transactions',
      'transactionsTotal',
      'transactionsLimit'
    ])
  },
  methods: {
    ...mapActions('history', [
      HistoryActions.FETCH_TRANSACTIONS,
      HistoryActions.IGNORE_ACTIONS,
      HistoryActions.UNIGNORE_ACTION
    ]),
    ...mapMutations(['setMessage'])
  }
})
export default class Transactions extends Mixins(StatusMixin) {
  fetchTransactions!: (source: FetchSource) => Promise<void>;
  ignoreActions!: (actionsIds: IgnoreActionPayload) => Promise<ActionStatus>;
  unignoreActions!: (actionsIds: IgnoreActionPayload) => Promise<ActionStatus>;
  setMessage!: (message: Message) => void;
  expanded = [];
  section = Section.TX;
  transactions!: EthTransactionWithFee[];
  transactionsTotal!: number;
  transactionsLimit!: number;
  page: number = 1;

  account: GeneralAccount | null = null;

  selected: string[] = [];

  getKey(tx: EthTransactionWithFee): string {
    return tx.txHash + tx.fromAddress + tx.nonce;
  }

  setSelected(selected: boolean) {
    const selection = this.selected;
    if (!selected) {
      const total = selection.length;
      for (let i = 0; i < total; i++) {
        selection.pop();
      }
    } else {
      for (const tx of this.visibleTransactions) {
        const key = this.getKey(tx);
        if (!key || selection.includes(key)) {
          continue;
        }
        selection.push(key);
      }
    }
  }

  selectionChanged(key: string, selected: boolean) {
    const selection = this.selected;
    if (!selected) {
      const index = selection.indexOf(key);
      if (index >= 0) {
        selection.splice(index, 1);
      }
    } else if (key && !selection.includes(key)) {
      selection.push(key);
    }
  }

  get allSelected(): boolean {
    const strings = this.visibleTransactions.map(tx => this.getKey(tx));
    return (
      strings.length > 0 && isEqual(sortBy(strings), sortBy(this.selected))
    );
  }

  async ignoreTransactions(ignore: boolean) {
    let status: ActionStatus;

    const actionIds = this.visibleTransactions
      .filter(tx => {
        const ignoredInAccounting = tx.ignoredInAccounting;
        const key = this.getKey(tx);
        return (
          (ignore ? !ignoredInAccounting : ignoredInAccounting) &&
          this.selected.includes(key)
        );
      })
      .map(tx => this.getKey(tx))
      .filter((value, index, array) => array.indexOf(value) === index);

    if (actionIds.length === 0) {
      const choice = ignore ? 1 : 2;
      this.setMessage({
        success: false,
        title: this.$tc('transactions.ignore.no_actions.title', choice),
        description: this.$tc(
          'transactions.ignore.no_actions.description',
          choice
        )
      });
      return;
    }

    const payload: IgnoreActionPayload = {
      actionIds: actionIds,
      type: IGNORE_TRANSACTIONS
    };
    if (ignore) {
      status = await this.ignoreActions(payload);
    } else {
      status = await this.unignoreActions(payload);
    }

    if (status.success) {
      const total = this.selected.length;
      for (let i = 0; i < total; i++) {
        this.selected.pop();
      }
    }
  }

  @Watch('account')
  onSelectionChange(account: GeneralAccount | null) {
    if (account) {
      this.page = 1;
    }
  }

  get visibleTransactions(): EthTransactionWithFee[] {
    const account = this.account;
    return account
      ? this.transactions
          .filter(
            ({ fromAddress, toAddress }) =>
              fromAddress === account.address || toAddress === account.address
          )
          .reduce((acc, tx) => {
            const index = acc.findIndex(({ txHash }) => txHash === tx.txHash);
            if (index >= 0) {
              if (acc[index].fromAddress !== account.address) {
                acc[index] = tx;
              }
            } else {
              acc.push(tx);
            }
            return acc;
          }, new Array<EthTransactionWithFee>())
      : this.transactions.filter(
          (tx, index, array) =>
            array.findIndex(tx2 => tx2.txHash === tx.txHash) === index
        );
  }

  readonly headers: DataTableHeader[] = [
    {
      text: '',
      value: 'selection',
      sortable: false
    },
    {
      text: this.$tc('transactions.headers.txhash'),
      value: 'txHash'
    },
    {
      text: this.$tc('transactions.headers.block'),
      value: 'blockNumber',
      align: 'end'
    },
    {
      text: this.$tc('transactions.headers.timestamp'),
      value: 'timestamp'
    },
    {
      text: this.$tc('transactions.headers.from_address'),
      value: 'fromAddress'
    },
    {
      text: this.$tc('transactions.headers.to_address'),
      value: 'toAddress'
    },
    {
      text: this.$tc('transactions.headers.value'),
      value: 'value',
      align: 'end'
    },
    {
      text: this.$tc('transactions.headers.gas_fee'),
      value: 'gasFee',
      align: 'end'
    },
    {
      text: this.$t('transactions.headers.ignored_in_accounting').toString(),
      value: 'ignoredInAccounting',
      width: '15px'
    },
    { text: '', value: 'data-table-expand' }
  ];

  async mounted() {
    await this.fetchTransactions(FETCH_FROM_CACHE);
    await this.fetchTransactions(FETCH_FROM_SOURCE);
  }

  async refresh() {
    await this.fetchTransactions(FETCH_REFRESH);
  }

  toEth(value: BigNumber): BigNumber {
    return toUnit(value, Unit.ETH);
  }
}
</script>

<style scoped lang="scss">
::v-deep {
  tbody {
    tr {
      > td {
        padding-top: 16px !important;
        padding-bottom: 16px !important;
      }
    }
  }
}
</style>
