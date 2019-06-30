<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-layout row align-center justify-center class="wrapper">
    <v-flex xs12>
      <v-autocomplete
        v-model="ownedTokens"
        :disabled="loading"
        :loading="loading"
        :items="allTokens"
        small-chips
        color="blue-grey lighten-2"
        label="Owned Tokens"
        item-text="symbol"
        :filter="filter"
        :menu-props="{ closeOnClick: true, closeOnContentClick: true }"
        item-value="symbol"
        multiple
        @input="add($event)"
      >
        <template v-slot:selection="data">
          <v-chip
            :selected="data.selected"
            close
            class="chip--select-multi"
            @input="remove(data.item)"
          >
            <v-avatar>
              <crypto-icon :symbol="data.item.symbol"></crypto-icon>
            </v-avatar>
            {{ data.item.symbol }}
          </v-chip>
        </template>
        <template v-slot:item="data">
          <template v-if="typeof data.item !== 'object'">
            <v-list-tile-content v-text="data.item"></v-list-tile-content>
          </template>
          <template v-else>
            <v-list-tile-avatar>
              <crypto-icon :symbol="data.item.symbol"></crypto-icon>
            </v-list-tile-avatar>
            <v-list-tile-content>
              <v-list-tile-title v-html="data.item.symbol"></v-list-tile-title>
              <v-list-tile-sub-title
                v-html="data.item.name"
              ></v-list-tile-sub-title>
            </v-list-tile-content>
          </template>
        </template>
      </v-autocomplete>
      <message-dialog
        :title="errorTitle"
        :message="errorMessage"
        @dismiss="dismiss()"
      ></message-dialog>
    </v-flex>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { EthToken } from '@/model/eth_token';
import CryptoIcon from '@/components/CryptoIcon.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { BlockchainAccountResult } from '@/model/blockchain_account_result';
import { convertBalances, convertEthBalances } from '@/utils/conversion';

@Component({
  components: {
    CryptoIcon,
    MessageDialog
  }
})
export default class TokenTrack extends Vue {
  allTokens: EthToken[] = [];
  ownedTokens: string[] = [];

  loading = false;

  errorTitle: string = '';
  errorMessage: string = '';

  add(tokens: string[]) {
    const symbol = tokens[tokens.length - 1];
    this.loading = true;
    this.$rpc
      .add_owned_eth_tokens([symbol])
      .then(result => {
        this.update(result);
      })
      .catch(reason => {
        this.removeToken(symbol);
        this.errorTitle = 'Token Addition Error';
        this.errorMessage = reason.message;
      })
      .finally(() => (this.loading = false));
  }

  remove(token: EthToken) {
    const symbol = token.symbol;
    this.loading = true;
    this.$rpc
      .remove_owned_eth_tokens([symbol])
      .then(result => {
        this.update(result);
        this.removeToken(symbol);
      })
      .catch(reason => {
        this.errorTitle = 'Token Removal Error';
        this.errorMessage = (reason as Error).message;
      })
      .finally(() => (this.loading = false));
  }

  private removeToken(symbol: string) {
    const index = this.ownedTokens.findIndex(owned => owned === symbol);
    if (index !== -1) {
      this.ownedTokens.splice(index, 1);
    }
  }

  created() {
    this.$rpc
      .get_eth_tokens()
      .then(result => {
        this.ownedTokens = result.owned_eth_tokens;
        this.allTokens = result.all_eth_tokens;
      })
      .catch((reason: Error) => {
        console.log(`Error at getting ETH tokens: ${reason.message}`);
      });
  }

  filter(token: EthToken, queryText: string): boolean {
    const { name, symbol } = token;
    const query = queryText.toLocaleLowerCase();
    return (
      name.toLocaleLowerCase().indexOf(query) > -1 ||
      symbol.toLocaleLowerCase().indexOf(query) > -1
    );
  }

  private update(result: BlockchainAccountResult) {
    const { per_account, totals } = result;
    const { ETH, BTC } = per_account;

    this.$store.commit('balances/updateEth', convertEthBalances(ETH));
    this.$store.commit('balances/updateBtc', convertBalances(BTC));
    this.$store.commit('balances/updateTotals', convertBalances(totals));
  }

  dismiss() {
    this.errorMessage = '';
    this.errorTitle = '';
  }
}
</script>

<style scoped lang="scss">
.wrapper {
  margin-top: 16px;
  margin-bottom: 16px;
}
.token-list {
  width: 200px;
  height: 300px;
  overflow-y: scroll;
}
</style>
