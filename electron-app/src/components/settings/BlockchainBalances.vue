<template>
  <v-layout>
    <v-flex>
      <v-card>
        <v-toolbar card>Blockchain Balance</v-toolbar>
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
          <v-divider></v-divider>
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
import { AccountBalance, EthBalances } from '@/model/blockchain-balances';
import { createNamespacedHelpers } from 'vuex';
import { convertEthBalances } from '@/utils/conversion';
import AccountBalances from '@/components/settings/AccountBalances.vue';
import { create_task } from '@/legacy/monitor';
import AssetBalances from '@/components/settings/AssetBalances.vue';

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

  created() {
    this.$rpc
      .query_blockchain_balances_async()
      .then(value => {
        create_task(
          value.task_id,
          'user_settings_query_blockchain_balances',
          'Query blockchain balances',
          false,
          true
        );
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
        if (blockchain === 'ETH') {
          const balances: EthBalances = convertEthBalances(
            result.per_account['ETH']
          );
          this.$store.commit('addPerAccountEth', balances);
        } else if (blockchain === 'BTC') {
          this.$store.commit('addPerAccountBtc', result.per_account['BTC']);
        }

        console.log(result['totals']);
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
