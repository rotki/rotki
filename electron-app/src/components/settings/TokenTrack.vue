<template>
  <v-layout row>
    <div v-if="loading" class="overlay">
      <v-progress-circular></v-progress-circular>
    </div>
    <v-flex xs2>
      <h4>All Eth Tokens</h4>
      <v-list class="token-list">
        <v-list-tile
          v-for="token in availableTokens"
          :key="token.address"
          avatar
          @click="addToken(token)"
        >
          <v-list-tile-content>
            <v-list-tile-title>{{ token.symbol }}</v-list-tile-title>
          </v-list-tile-content>
        </v-list-tile>
      </v-list>
    </v-flex>
    <v-flex xs2>
      <h4>My ETH Tokens</h4>
      <v-list class="token-list">
        <v-list-tile
          v-for="token in ownedTokens"
          :key="token"
          avatar
          @click="removeToken(token)"
        >
          <v-list-tile-content>
            <v-list-tile-title>{{ token }}</v-list-tile-title>
          </v-list-tile-content>
        </v-list-tile>
      </v-list>
    </v-flex>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { EthToken } from '@/model/eth_token';

@Component({})
export default class TokenTrack extends Vue {
  allTokens: EthToken[] = [];
  ownedTokens: string[] = [];

  loading = false;

  get availableTokens(): EthToken[] {
    return this.allTokens.filter(
      token =>
        this.ownedTokens.findIndex(
          ownedToken => ownedToken === token.symbol
        ) === -1
    );
  }

  errorTitle: string = '';
  errorMessage: string = '';

  addToken(token: EthToken) {
    this.loading = true;
    this.$rpc
      .add_owned_eth_tokens([token.symbol])
      .then(result => {
        this.ownedTokens.push(token.symbol);
        console.log(result);
      })
      .catch(reason => {
        this.errorTitle = 'Token Addition Error';
        this.errorMessage = reason.message;
      })
      .finally(() => (this.loading = false));
  }

  removeToken(token: string) {
    this.loading = true;
    this.$rpc
      .remove_owned_eth_tokens([token])
      .then(result => {
        console.log(result);
        const index = this.ownedTokens.findIndex(owned => owned === token);
        if (index !== -1) {
          this.ownedTokens.splice(index, 1);
        }
      })
      .catch(reason => {
        this.errorTitle = 'Token Removal Error';
        this.errorMessage = (reason as Error).message;
      })
      .finally(() => (this.loading = false));
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
}
</script>

<style scoped lang="scss">
.token-list {
  max-width: 180px;
  height: 300px;
  overflow-y: scroll;
}
</style>
