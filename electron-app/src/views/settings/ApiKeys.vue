<template>
  <v-container class="api-keys">
    <v-row>
      <v-col>
        <h1>API Keys</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        Rotki can communciate with various APIs to provide additional
        functionality. Click each tab below to explore what is offered.
      </v-col>
    </v-row>
    <v-tabs grow>
      <v-tab>Rotki Premium</v-tab>
      <v-tab>Exchanges</v-tab>
      <v-tab>External Services</v-tab>
      <v-tab-item><premium-settings></premium-settings></v-tab-item>
      <v-tab-item><exchange-settings></exchange-settings></v-tab-item>
      <v-tab-item><external-services></external-services></v-tab-item>
    </v-tabs>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import BlockchainBalances from '@/components/accounts/BlockchainBalances.vue';
import FiatBalances from '@/components/accounts/FiatBalances.vue';
import ExchangeSettings from '@/components/settings/api-keys/ExchangeSettings.vue';
import ExternalServices from '@/components/settings/api-keys/ExternalServices.vue';
import PremiumSettings from '@/components/settings/PremiumSettings.vue';

@Component({
  components: {
    BlockchainBalances,
    FiatBalances,
    ExchangeSettings,
    ExternalServices,
    PremiumSettings
  }
})
export default class ApiKeys extends Vue {}
</script>

<style scoped lang="scss">
.api-keys > * {
  margin-bottom: 16px;
}
</style>
