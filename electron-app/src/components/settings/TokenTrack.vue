<template>
  <v-row align="center" justify="center" class="token-track">
    <v-col cols="12">
      <v-autocomplete
        v-model="ownedTokens"
        :disabled="loading"
        :loading="loading"
        :items="allTokens"
        class="token-track__search"
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
        <template #selection="data">
          <v-chip
            :id="`token-chip__${data.item.symbol.toLocaleLowerCase()}`"
            :input-value="data.selected"
            close
            class="chip--select-multi token-track__chip"
            @click:close="remove(data.item)"
            @click="data.select"
          >
            <v-avatar>
              <crypto-icon :symbol="data.item.symbol"></crypto-icon>
            </v-avatar>
            <span class="token-track__chip__text">
              {{ data.item.symbol }}
            </span>
          </v-chip>
        </template>
        <template #item="data">
          <template v-if="typeof data.item !== 'object'">
            <v-list-item-content v-text="data.item"></v-list-item-content>
          </template>
          <template v-else>
            <v-list-item-avatar>
              <crypto-icon :symbol="data.item.symbol"></crypto-icon>
            </v-list-item-avatar>
            <v-list-item-content>
              <v-list-item-title>{{ data.item.symbol }}</v-list-item-title>
              <v-list-item-subtitle>{{ data.item.name }}</v-list-item-subtitle>
            </v-list-item-content>
          </template>
        </template>
      </v-autocomplete>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { EthToken } from '@/model/eth_token';
import CryptoIcon from '@/components/CryptoIcon.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { BlockchainAccountResult } from '@/model/blockchain_account_result';
import { convertBalances, convertEthBalances } from '@/utils/conversion';
import { Message } from '@/store/store';

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
        this.$store.commit('setMessage', {
          title: 'Token Addition Error',
          description: (reason as Error).message
        } as Message);
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
        this.$store.commit('setMessage', {
          title: 'Token Removal Error',
          description: (reason as Error).message
        } as Message);
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
    const { commit } = this.$store;

    commit('balances/updateEth', convertEthBalances(ETH));
    commit('balances/updateBtc', convertBalances(BTC));
    commit('balances/updateTotals', convertBalances(totals));
  }
}
</script>

<style scoped lang="scss">
.token-track {
  margin-top: 16px;
  margin-bottom: 16px;
}

.token-track__chip__text {
  margin-left: 8px;
}
</style>
