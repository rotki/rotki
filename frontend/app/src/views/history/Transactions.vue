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
              item-key="txHash"
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
              </template>
              <template #item.fromAddress="{ item }">
                <hash-link :text="item.fromAddress" />
              </template>
              <template #item.toAddress="{ item }">
                <hash-link :text="item.toAddress" />
              </template>
              <template #item.timestamp="{ item }">
                <date-display :timestamp="item.timestamp" />
              </template>
              <template #item.value="{ item }">
                <amount-display :value="toEth(item.value)" asset="ETH" />
              </template>
              <template #item.gasFee="{ item }">
                <amount-display :value="gasFee(item)" asset="ETH" />
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
import { EthTransaction } from '@/services/history/types';
import { Section } from '@/store/const';
import { GeneralAccount } from '@/typing/types';
import { toEth } from '@/utils/calculation';

type EthTransactionWithFee = EthTransaction & { gasFee: BigNumber };

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
  transactions!: EthTransaction[];
  transactionsTotal!: number;
  transactionsLimit!: number;
  toEth = toEth;
  page: number = 1;

  account: GeneralAccount | null = null;

  @Watch('account')
  onSelectionChange(account: GeneralAccount | null) {
    if (account) {
      this.page = 1;
    }
  }

  get visibleTransactions(): EthTransactionWithFee[] {
    const selectedTransactions = this.account
      ? this.transactions.filter(tx => tx.fromAddress === this.account.address)
      : this.transactions;
    return selectedTransactions.map(value => ({
      ...value,
      gasFee: this.gasFee(value)
    }));
  }

  gasFee(item: EthTransaction): BigNumber {
    return toEth(item.gasPrice.multipliedBy(item.gasUsed));
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
