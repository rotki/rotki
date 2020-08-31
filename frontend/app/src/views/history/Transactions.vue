<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('transactions.loading') }}
    </template>
    {{ $t('transactions.loading_subtitle') }}
  </progress-screen>
  <v-container v-else>
    <blockchain-account-selector v-model="account" hint :chains="['ETH']" />
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            {{ $t('transactions.title') }}
            <v-spacer />
            <refresh-button
              :loading="refreshing"
              :tooltip="$t('transactions.refresh_tooltip')"
              @refresh="fetchTransactions(true)"
            />
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="headers"
              :items="visibleTransactions"
              show-expand
              single-expand
              :expanded="expanded"
              item-key="key"
              sort-by="timestamp"
              sort-desc
              :page.sync="page"
              :footer-props="footerProps"
              :loading="refreshing"
            >
              <template #item.txHash="{ item }">
                <hash-link
                  :text="item.txHash"
                  base-url="https://etherscan.io/tx/"
                />
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
                  transactionsLimit <= transactionsTotal &&
                  transactionsLimit > 0
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
                <td :colspan="headers.length" class="transactions__details">
                  <transaction-details :transaction="item" />
                </td>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Mixins, Watch } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters } from 'vuex';
import DateDisplay from '@/components/display/DateDisplay.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import HashLink from '@/components/helper/HashLink.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TransactionDetails from '@/components/history/TransactionsDetails.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { footerProps } from '@/config/datatable.common';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import { EthTransactionWithFee } from '@/store/history/types';
import { GeneralAccount } from '@/typing/types';
import { toUnit, Unit } from '@/utils/calculation';

@Component({
  components: {
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
    ...mapActions('history', ['fetchTransactions'])
  }
})
export default class Transactions extends Mixins(StatusMixin) {
  fetchTransactions!: (refresh: boolean) => Promise<void>;
  footerProps = footerProps;
  expanded = [];
  section = Section.TX;
  transactions!: EthTransactionWithFee[];
  transactionsTotal!: number;
  transactionsLimit!: number;
  page: number = 1;

  account: GeneralAccount | null = null;

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
    { text: '', value: 'data-table-expand' }
  ];

  mounted() {
    this.fetchTransactions(false);
  }

  toEth(value: BigNumber): BigNumber {
    return toUnit(value, Unit.ETH);
  }
}
</script>

<style scoped lang="scss">
.transactions {
  &__details {
    box-shadow: inset 1px 8px 10px -10px;
    background-color: var(--v-rotki-light-grey-base);
  }
}
</style>
