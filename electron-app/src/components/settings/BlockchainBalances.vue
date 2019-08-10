import { TaskType } from "@/model/task";
<template>
  <v-layout>
    <v-flex>
      <v-card>
        <v-card-title>Blockchain Balance</v-card-title>
        <v-card-text>
          <v-select
            v-model="selected"
            :items="items"
            label="Choose blockchain"
          ></v-select>
          <v-text-field v-model="accountAddress" label="Account"></v-text-field>
          <v-btn
            id="add-blockchain-account"
            depressed
            color="primary"
            type="submit"
            :disabled="!accountAddress"
            @click="addAccount()"
          >
            Add
          </v-btn>

          <token-track></token-track>
          <v-divider></v-divider>
          <asset-balances
            title="Blockchain Balances per Asset"
            :balances="totals"
          >
          </asset-balances>
          <v-divider></v-divider>
          <account-balances
            title="ETH per account balances"
            name="ETH"
            :balances="ethAccounts"
          ></account-balances>
          <v-divider></v-divider>
          <account-balances
            title="BTC per account balances"
            name="BTC"
            :balances="btcAccounts"
          ></account-balances>
        </v-card-text>
      </v-card>
    </v-flex>
    <message-dialog
      :title="errorTitle"
      :message="errorMessage"
      @dismiss="dismiss()"
    ></message-dialog>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import TokenTrack from '@/components/settings/TokenTrack.vue';
import { AccountBalance } from '@/model/blockchain-balances';
import { createNamespacedHelpers } from 'vuex';
import { convertBalances, convertEthBalances } from '@/utils/conversion';
import AccountBalances from '@/components/settings/AccountBalances.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import { createTask, TaskType } from '@/model/task';

const { mapGetters } = createNamespacedHelpers('balances');

@Component({
  components: { AccountBalances, AssetBalances, TokenTrack, MessageDialog },
  computed: mapGetters(['ethAccounts', 'btcAccounts', 'totals'])
})
export default class BlockchainBalances extends Vue {
  selected: 'ETH' | 'BTC' = 'ETH';
  readonly items: string[] = ['ETH', 'BTC'];
  accountAddress: string = '';

  errorTitle: string = '';
  errorMessage: string = '';

  ethAccounts!: AccountBalance[];
  btcAccounts!: AccountBalance[];
  totals!: AccountBalance[];

  mounted() {
    this.$rpc
      .query_blockchain_balances_async()
      .then(value => {
        console.log(value);
        const task = createTask(
          value.task_id,
          TaskType.USER_SETTINGS_QUERY_BLOCKCHAIN_BALANCES,
          'Query blockchain balances',
          true
        );
        this.$store.commit('tasks/addBalanceTask', task);
      })
      .catch((reason: Error) => {
        console.log(
          `Error at querying blockchain balances async: ${reason.message}`
        );
      });
  }

  addAccount() {
    const account = this.accountAddress;
    const blockchain = this.selected;
    this.$rpc
      .add_blockchain_account(blockchain, account)
      .then(result => {
        const { per_account, totals } = result;
        if (blockchain === 'ETH') {
          const { ETH } = per_account;
          this.$store.commit('balances/updateEth', convertEthBalances(ETH));
        } else if (blockchain === 'BTC') {
          const { BTC } = per_account;
          this.$store.commit('balances/updateBtc', convertBalances(BTC));
        }
        this.$store.commit('balances/updateTotals', convertBalances(totals));
      })
      .catch((reason: Error) => {
        this.errorTitle = 'Account Error';
        this.errorMessage = `Error at adding new ${blockchain} account: ${reason.message}`;
      });
  }

  dismiss() {
    this.errorTitle = '';
    this.errorMessage = '';
  }
}
</script>

<style scoped></style>
