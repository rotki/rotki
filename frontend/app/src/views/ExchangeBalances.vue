<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="page-header">{{ exchange }} Balances</h1>
      </v-col>
    </v-row>
    <v-card>
      <asset-balances :balances="exchangeBalances(exchange)"></asset-balances>
    </v-card>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';

const { mapState, mapGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AssetBalances,
    CryptoIcon
  },
  computed: {
    ...mapState(['connectedExchanges']),
    ...mapGetters(['exchangeBalances'])
  }
})
export default class ExchangeBalances extends Vue {
  connectedExchanges!: string[];
  exchangeBalances!: (exchange: string) => AssetBalances[];

  get exchange(): string {
    return this.$route.params.exchange;
  }

  mounted() {
    const exchangeIndex = this.connectedExchanges.indexOf(this.exchange);
    if (exchangeIndex < 0) {
      this.$router.push({ name: 'dashboard' });
    }
  }
}
</script>

<style scoped></style>
