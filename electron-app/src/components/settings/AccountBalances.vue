<template>
  <div
    class="balance-table"
    :class="`${blockchain.toLocaleLowerCase()}-balance-table`"
  >
    <v-row>
      <v-col>
        <h3 class="text-center balance-table__title">{{ title }}</h3>
      </v-col>
    </v-row>
    <v-data-table
      :headers="headers"
      :items="balances"
      :loading="deleting"
      single-expand
      item-key="account"
      :expanded.sync="expanded"
      :show-expand="expandable"
    >
      <template #header.usdValue>
        {{ currency.ticker_symbol }} value
      </template>
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
      <template v-slot:expanded-item="{ headers, item }">
        <td :colspan="headers.length" class="asset-balances__expanded">
          <account-asset-balances
            :account="item.account"
          ></account-asset-balances>
        </td>
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

const { mapGetters } = createNamespacedHelpers('session');
const { mapGetters: mapBalancesGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AccountAssetBalances,
    AssetBalances,
    ConfirmDialog
  },
  computed: {
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapBalancesGetters(['exchangeRate'])
  }
})
export default class AccountBalances extends Vue {
  @Prop({ required: true })
  balances!: AccountBalance[];
  @Prop({ required: true })
  blockchain!: string;
  @Prop({ required: true })
  title!: string;

  expanded = [];

  get expandable(): boolean {
    return this.blockchain === 'ETH';
  }

  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  toDeleteAccount: string = '';
  deleting = false;

  headers = [
    { text: 'Account', value: 'account' },
    { text: this.blockchain, value: 'amount' },
    { text: 'USD Value', value: 'usdValue' },
    { text: 'Actions', value: 'actions', sortable: false, width: '50' },
    { text: '', value: 'data-table-expand' }
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
