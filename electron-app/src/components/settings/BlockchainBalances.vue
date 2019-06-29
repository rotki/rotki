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
          <token-track></token-track>
          <per-account-balance
            name="ETH"
            :balances="perAccountEth"
          ></per-account-balance>
          <per-account-balance name="BTC" :balances="perAccountBtc">
          </per-account-balance>
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
import { mapGetters } from 'vuex';
import PerAccountBalance from '@/components/settings/PerAccountBalance.vue';
import { convertEthBalances } from '@/utils/conversion';

@Component({
  components: { PerAccountBalance, TokenTrack, MessageDialog },
  computed: mapGetters(['perAccountEth'])
})
export default class BlockchainBalances extends Vue {
  selected: 'ETH' | 'BTC' = 'ETH';
  readonly items: string[] = ['ETH', 'BTC'];
  accountAddress: string = '';

  errorTitle: string = '';
  errorMessage: string = '';

  perAccountEth!: AccountBalance[];
  perAccountBtc: AccountBalance[] = [];

  created() {}

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
