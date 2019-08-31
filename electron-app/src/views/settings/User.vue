<template>
  <v-container class="user-settings">
    <v-row>
      <v-col>
        <h1>User Settings</h1>
      </v-col>
    </v-row>
    <premium-settings></premium-settings>
    <exchange-settings></exchange-settings>
    <fiat-balances></fiat-balances>
    <blockchain-balances></blockchain-balances>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import PremiumSettings from '@/components/settings/PremiumSettings.vue';
import ExchangeSettings from '@/components/settings/ExchangeSettings.vue';
import FiatBalances from '@/components/settings/FiatBalances.vue';
import BlockchainBalances from '@/components/settings/BlockchainBalances.vue';

@Component({
  components: {
    BlockchainBalances,
    FiatBalances,
    ExchangeSettings,
    PremiumSettings
  }
})
export default class User extends Vue {}
</script>

<style scoped lang="scss">
.user-settings > * {
  margin-bottom: 20px;
}
</style>
