<template>
  <div
    class="balance-table"
    :class="`${blockchain.toLocaleLowerCase()}-balance-table`"
  >
    <v-row>
      <v-col cols="11">
        <h3 class="text-center balance-table__title">{{ title }}</h3>
      </v-col>
      <v-col cols="1">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn
              class="balance-table__refresh"
              color="primary"
              text
              icon
              :disabled="isLoading"
              v-on="on"
              @click="refresh()"
            >
              <v-icon>fa-refresh</v-icon>
            </v-btn>
          </template>
          <span>
            Refreshes the {{ blockchain }} balances ignoring any cached entries
          </span>
        </v-tooltip>
      </v-col>
    </v-row>
    <v-data-table
      :headers="headers"
      :items="balances"
      :loading="deleting || isLoading"
      loading-text="Please wait while Rotki fetches your balances..."
      single-expand
      item-key="account"
      :expanded.sync="expanded"
    >
      <template #header.usdValue> {{ currency.ticker_symbol }} value </template>
      <template #item.account="{ item }">
        {{ item.account }}
      </template>
      <template #item.amount="{ item }">
        {{ item.amount | formatPrice(floatingPrecision) }}
      </template>
      <template #item.usdValue="{ item }">
        {{
          item.usdValue
            | calculatePrice(exchangeRate(currency.ticker_symbol))
            | formatPrice(floatingPrecision)
        }}
      </template>
      <template #item.actions="{ item }">
        <v-icon
          small
          :disabled="deleting"
          @click="toDeleteAccount = item.account"
        >
          fa-trash
        </v-icon>
      </template>
      <template v-if="balances.length > 0" #body.append>
        <tr class="balance-table__totals">
          <td>Totals</td>
          <td>
            {{
              balances.map(val => val.amount)
                | balanceSum
                | formatPrice(floatingPrecision)
            }}
          </td>
          <td>
            {{
              balances.map(val => val.usdValue)
                | balanceSum
                | calculatePrice(exchangeRate(currency.ticker_symbol))
                | formatPrice(floatingPrecision)
            }}
          </td>
        </tr>
      </template>
      <template #expanded-item="{ headers, item }">
        <td :colspan="headers.length" class="asset-balances__expanded">
          <account-asset-balances
            :account="item.account"
          ></account-asset-balances>
        </td>
      </template>
      <template #item.expand="{ item }">
        <span v-if="expandable && hasTokens(item.account)">
          <v-icon v-if="expanded.includes(item)" @click="expanded = []">
            fa fa-angle-up
          </v-icon>
          <v-icon v-else @click="expanded = [item]">fa fa-angle-down</v-icon>
        </span>
      </template>
    </v-data-table>
    <confirm-dialog
      :display="toDeleteAccount !== ''"
      title="Account delete"
      :message="`Are you sure you want to delete ${toDeleteAccount}`"
      @cancel="toDeleteAccount = ''"
      @confirm="deleteAccount()"
    ></confirm-dialog>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { AccountBalance } from '@/model/blockchain-balances';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import AccountAssetBalances from '@/components/settings/AccountAssetBalances.vue';
import { Blockchain } from '@/typing/types';
import { BlockchainBalancePayload } from '@/store/balances/actions';
import { TaskType } from '@/model/task';

const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');
const { mapGetters } = createNamespacedHelpers('session');
const { mapGetters: mapBalancesGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AccountAssetBalances,
    AssetBalances,
    ConfirmDialog
  },
  computed: {
    ...mapTaskGetters(['isTaskRunning']),
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapBalancesGetters(['exchangeRate', 'hasTokens'])
  }
})
export default class AccountBalances extends Vue {
  @Prop({ required: true })
  balances!: AccountBalance[];
  @Prop({ required: true })
  blockchain!: Blockchain;
  @Prop({ required: true })
  title!: string;

  isTaskRunning!: (type: TaskType) => boolean;

  get isLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  }

  expanded = [];

  get expandable(): boolean {
    return this.blockchain === 'ETH';
  }

  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
  hasTokens!: (account: string) => boolean;

  toDeleteAccount: string = '';
  deleting = false;

  headers = [
    { text: 'Account', value: 'account' },
    { text: this.blockchain, value: 'amount' },
    { text: 'USD Value', value: 'usdValue' },
    { text: 'Actions', value: 'actions', sortable: false, width: '50' },
    { text: '', value: 'expand', align: 'end' }
  ];

  async deleteAccount() {
    const address = this.toDeleteAccount;
    const blockchain = this.blockchain;
    this.toDeleteAccount = '';
    this.deleting = true;

    await this.$store.dispatch('balances/removeAccount', {
      address,
      blockchain
    });
    this.deleting = false;
  }

  refresh() {
    this.$store.dispatch('balances/fetchBlockchainBalances', {
      ignoreCache: true,
      blockchain: this.blockchain
    } as BlockchainBalancePayload);
  }
}
</script>

<style scoped lang="scss">
.balance-table {
  margin-top: 16px;
  margin-bottom: 16px;
}

.balance-table__totals {
  font-weight: 500;
}

.asset-balances__expanded {
  padding: 0 !important;
}
</style>
