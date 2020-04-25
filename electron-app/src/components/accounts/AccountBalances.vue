<template>
  <div
    class="account-balances"
    :class="`${blockchain.toLocaleLowerCase()}-account-balances`"
  >
    <v-row>
      <v-col cols="11">
        <h3 class="text-center account-balances__title">{{ title }}</h3>
      </v-col>
      <v-col cols="1">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn
              class="account-balances__refresh"
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
    <v-row>
      <v-col cols="6" offset="6">
        <tag-filter v-model="onlyTags"></tag-filter>
      </v-col>
    </v-row>
    <v-data-table
      :headers="headers"
      :items="visibleBalances"
      :loading="accountOperation || isLoading"
      loading-text="Please wait while Rotki queries the blockchain..."
      single-expand
      item-key="account"
      :expanded.sync="expanded"
      sort-by="usdValue"
      sort-desc
    >
      <template v-if="blockchain === 'ETH'" #header.usdValue>
        Total {{ currency.ticker_symbol }} value of account's assets
      </template>
      <template v-else #header.usdValue>
        {{ currency.ticker_symbol }} value
      </template>
      <template #item.account="{ item }">
        <v-row>
          <v-col cols="12" class="account-balances__account">
            <span
              v-if="!accountLabel(blockchain, item.account)"
              class="account-balances__account__address"
            >
              {{ item.account }}
            </span>
            <v-tooltip v-else top>
              <template #activator="{ on }">
                <span class="account-balances__account__address" v-on="on">
                  {{ accountLabel(blockchain, item.account) }}
                </span>
              </template>
              <span> {{ item.account }} </span>
            </v-tooltip>
            <span v-if="accountTags(blockchain, item.account)">
              <tag-icon
                v-for="tag in accountTags(blockchain, item.account)"
                :key="tag"
                class="account-balances__tag"
                :tag="tags[tag]"
              ></tag-icon>
            </span>
          </v-col>
        </v-row>
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount"></amount-display>
      </template>
      <template #item.usdValue="{ item }">
        <amount-display fiat :value="item.usdValue"></amount-display>
      </template>
      <template #item.actions="{ item }">
        <span class="account-balances__actions">
          <v-icon
            small
            class="mr-2"
            :disabled="accountOperation"
            @click="editedAccount = item.account"
          >
            fa-edit
          </v-icon>
          <v-icon
            small
            class="mr-2"
            :disabled="accountOperation"
            @click="toDeleteAccount = item.account"
          >
            fa-trash
          </v-icon>
        </span>
      </template>
      <template v-if="balances.length > 0" #body.append>
        <tr class="account-balances__total">
          <td>Total</td>
          <td>
            {{
              visibleBalances.map(val => val.amount)
                | balanceSum
                | formatPrice(floatingPrecision)
            }}
          </td>
          <td>
            {{
              visibleBalances.map(val => val.usdValue)
                | balanceSum
                | calculatePrice(exchangeRate(currency.ticker_symbol))
                | formatPrice(floatingPrecision)
            }}
          </td>
        </tr>
      </template>
      <template #expanded-item="{ headers, item }">
        <td :colspan="headers.length" class="account-balances__expanded">
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
    <v-dialog
      max-width="600"
      persistent
      :value="!!editedAccount"
      @input="editedAccount = ''"
    >
      <v-card>
        <v-card-title>
          Edit Account
        </v-card-title>
        <v-card-subtitle>
          Modify labels and tags for the account
        </v-card-subtitle>
        <v-card-text>
          <account-form
            :edit="edited"
            @edit-complete="editedAccount = ''"
          ></account-form>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AccountForm from '@/components/accounts/AccountForm.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import AccountAssetBalances from '@/components/settings/AccountAssetBalances.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { AccountBalance } from '@/model/blockchain-balances';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task';
import { BlockchainBalancePayload } from '@/store/balances/actions';
import { Account, Blockchain, Tags } from '@/typing/types';

const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');
const { mapGetters, mapState } = createNamespacedHelpers('session');
const { mapGetters: mapBalancesGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AmountDisplay,
    AccountForm,
    TagFilter,
    TagIcon,
    AccountAssetBalances,
    AssetBalances,
    ConfirmDialog
  },
  computed: {
    ...mapTaskGetters(['isTaskRunning']),
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapState(['tags']),
    ...mapBalancesGetters([
      'exchangeRate',
      'hasTokens',
      'accountTags',
      'accountLabel'
    ])
  }
})
export default class AccountBalances extends Vue {
  @Prop({ required: true })
  balances!: AccountBalance[];
  @Prop({ required: true })
  blockchain!: Blockchain;
  @Prop({ required: true })
  title!: string;

  editedAccount = '';
  onlyTags: string[] = [];
  expanded = [];

  isTaskRunning!: (type: TaskType) => boolean;
  accountTags!: (blockchain: Blockchain, address: string) => string[];
  accountLabel!: (blockchain: Blockchain, address: string) => string;
  tags!: Tags;

  get edited(): Account | null {
    return this.editedAccount
      ? { address: this.editedAccount, chain: this.blockchain }
      : null;
  }

  get isLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  }

  get expandable(): boolean {
    return this.blockchain === 'ETH';
  }

  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
  hasTokens!: (account: string) => boolean;

  toDeleteAccount: string = '';
  pending = false;

  headers = [
    { text: 'Account', value: 'account' },
    { text: this.blockchain, value: 'amount' },
    { text: 'USD Value', value: 'usdValue' },
    { text: 'Actions', value: 'actions', sortable: false, width: '50' },
    { text: '', value: 'expand', align: 'end' }
  ];

  get visibleBalances(): AccountBalance[] {
    if (this.onlyTags.length === 0) {
      return this.balances;
    }

    const blockchain = this.blockchain;
    const accountTags = this.accountTags;
    const filteredTags = this.onlyTags;
    return this.balances.filter(({ account }) => {
      const tags = accountTags(blockchain, account);
      return filteredTags.every(tag => tags.includes(tag));
    });
  }

  get accountOperation(): boolean {
    return (
      this.isTaskRunning(TaskType.ADD_ACCOUNT) ||
      this.isTaskRunning(TaskType.REMOVE_ACCOUNT) ||
      this.pending
    );
  }

  async deleteAccount() {
    const address = this.toDeleteAccount;
    const blockchain = this.blockchain;
    this.toDeleteAccount = '';
    this.pending = true;

    await this.$store.dispatch('balances/removeAccount', {
      address,
      blockchain
    });
    this.pending = false;
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
.account-balances {
  margin-top: 16px;
  margin-bottom: 16px;

  &__account {
    display: flex;
    flex-direction: column;
    &__address {
      font-weight: 500;
      padding-top: 6px;
      padding-bottom: 6px;
    }
  }

  &__actions {
    display: flex;
    flex-direction: row;
  }

  &__total {
    font-weight: 500;
  }

  &__expanded {
    padding: 0 !important;
  }

  &__tag {
    margin-right: 8px;
    margin-bottom: 2px;
  }
}
</style>
