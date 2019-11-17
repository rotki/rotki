<template>
  <v-row class="account-asset-balances" align="center" justify="center">
    <v-col cols="12">
      <v-data-table
        :items="tokens"
        :headers="headers"
        class="account-asset-balances__table"
      >
        <template #item.asset="{ item }">
          <span class="account-asset-balances__balance__asset">
            <crypto-icon
              width="26px"
              class="account-asset-balances__balance__asset__icon"
              :symbol="item.asset"
            ></crypto-icon>
            {{ item.asset }}
          </span>
        </template>
        <template #item.amount="{ item }">
          {{ item.amount | formatPrice(floatingPrecision) }}
        </template>
      </v-data-table>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import CryptoIcon from '@/components/CryptoIcon.vue';
import { AssetBalances } from '@/model/blockchain-balances';
import { createNamespacedHelpers } from 'vuex';

const { mapGetters } = createNamespacedHelpers('balances');
const { mapGetters: mapSessionGetters } = createNamespacedHelpers('session');

@Component({
  components: { CryptoIcon },
  computed: {
    ...mapGetters(['accountTokens']),
    ...mapSessionGetters(['floatingPrecision'])
  }
})
export default class AccountAssetBalances extends Vue {
  @Prop({ required: true })
  account!: string;
  accountTokens!: (account: string) => AssetBalances[];
  floatingPrecision!: number;

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Amount', value: 'amount' }
  ];

  get tokens(): AssetBalances[] {
    return this.accountTokens(this.account);
  }
}
</script>

<style scoped lang="scss">
.account-asset-balances {
  background-color: #fafafa;
}

.account-asset-balances ::v-deep .v-data-table {
  background-color: #fafafa;
}

.account-asset-balances__table {
  margin-left: 12px;
  margin-right: 12px;
}

.account-asset-balances__balance__asset {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.account-asset-balances__balance__asset__icon {
  margin-right: 8px;
}
</style>
