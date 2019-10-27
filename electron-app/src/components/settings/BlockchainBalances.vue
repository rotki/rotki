<template>
  <v-row class="blockchain-balances">
    <v-col>
      <v-card>
        <v-card-title>Blockchain Balance</v-card-title>
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

  ethAccounts!: AccountBalance[];
  btcAccounts!: AccountBalance[];
  totals!: AccountBalance[];

  loading: boolean = false;

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
      console.error(e);
    }
    this.loading = false;
  }
}
</script>

<style scoped lang="scss">
.blockchain-balances--progress {
  height: 15px;
}
</style>
