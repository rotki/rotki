import { Severity } from "@/typing/types";
<template>
  <v-row class="blockchain-balances">
    <v-col>
      <v-card>
        <v-card-title>
          <span>Blockchain Balances</span>
          <v-spacer></v-spacer>
          <v-tooltip bottom>
            <template #activator="{ on }">
              <v-btn color="primary" text icon v-on="on" @click="refresh()">
                <v-icon>fa-refresh</v-icon>
              </v-btn>
            </template>
            <span>
              Refreshes the blockchain balances ignoring any cached entries
            </span>
          </v-tooltip>
        </v-card-title>
        <v-card-text>
          <v-select
            v-model="selected"
            class="blockchain-balances__chain"
            :items="items"
            label="Choose blockchain"
            :disabled="loading"
          ></v-select>
          <v-text-field
            v-model="accountAddress"
            class="blockchain-balances__address"
            label="Account"
            :disabled="loading"
          ></v-text-field>

          <div class="blockchain-balances--progress">
            <v-progress-linear v-if="loading" indeterminate></v-progress-linear>
          </div>

          <v-btn
            class="blockchain-balances__buttons__add"
            depressed
            color="primary"
            type="submit"
            :disabled="!accountAddress || loading"
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
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import TokenTrack from '@/components/settings/TokenTrack.vue';
import { AccountBalance } from '@/model/blockchain-balances';
import { createNamespacedHelpers } from 'vuex';
import AccountBalances from '@/components/settings/AccountBalances.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import { notify } from '@/store/notifications/utils';
import { Severity } from '@/typing/types';

const { mapGetters } = createNamespacedHelpers('balances');

@Component({
  components: { AccountBalances, AssetBalances, TokenTrack, MessageDialog },
  computed: mapGetters(['ethAccounts', 'btcAccounts', 'totals'])
})
export default class BlockchainBalances extends Vue {
  selected: 'ETH' | 'BTC' = 'ETH';
  readonly items: string[] = ['ETH', 'BTC'];
  accountAddress: string = '';

  ethAccounts!: AccountBalance[];
  btcAccounts!: AccountBalance[];
  totals!: AccountBalance[];

  loading: boolean = false;

  async addAccount() {
    const address = this.accountAddress;
    const blockchain = this.selected;
    this.loading = true;
    try {
      await this.$store.dispatch('balances/addAccount', {
        blockchain,
        address
      });
      this.accountAddress = '';
    } catch (e) {
      notify(
        `Error while adding account: ${e}`,
        'Adding Account',
        Severity.ERROR
      );
    }
    this.loading = false;
  }

  refresh() {
    this.$store.dispatch('balances/fetchBlockchainBalances', true);
  }
}
</script>

<style scoped lang="scss">
.blockchain-balances--progress {
  height: 15px;
}
</style>
