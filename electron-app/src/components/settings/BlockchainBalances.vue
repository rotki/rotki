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

@Component({
  components: { TokenTrack, MessageDialog }
})
export default class BlockchainBalances extends Vue {
  selected: 'ETH' | 'BTC' = 'ETH';
  readonly items: string[] = ['ETH', 'BTC'];
  accountAddress: string = '';

  errorTitle: string = '';
  errorMessage: string = '';

  addAccount() {
    const account = this.accountAddress;
    const blockchain = this.selected;
    this.$rpc
      .add_blockchain_account(blockchain, account)
      .then(result => {
        if (blockchain === 'ETH') {
          let perAccountElement = result.per_account['ETH'];
          console.log(perAccountElement);
        } else if (blockchain === 'BTC') {
          let perAccountElement = result.per_account['BTC'];
          console.log(perAccountElement);
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
