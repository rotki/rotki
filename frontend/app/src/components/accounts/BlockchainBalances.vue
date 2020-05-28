<template>
  <v-row class="blockchain-balances">
    <v-col>
      <v-card>
        <v-card-title>Blockchain Balances</v-card-title>
        <v-card-text>
          <account-form></account-form>
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
            blockchain="ETH"
            :balances="ethAccounts"
          ></account-balances>
          <v-divider></v-divider>
          <account-balances
            title="BTC per account balances"
            blockchain="BTC"
            :balances="btcAccounts"
          ></account-balances>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import AccountForm from '@/components/accounts/AccountForm.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import TokenTrack from '@/components/settings/TokenTrack.vue';
import { AccountBalance } from '@/model/blockchain-balances';

const { mapGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AccountForm,
    AccountBalances,
    AssetBalances,
    TokenTrack
  },
  computed: {
    ...mapGetters(['ethAccounts', 'btcAccounts', 'totals'])
  }
})
export default class BlockchainBalances extends Vue {
  ethAccounts!: AccountBalance[];
  btcAccounts!: AccountBalance[];
  totals!: AccountBalance[];
}
</script>
