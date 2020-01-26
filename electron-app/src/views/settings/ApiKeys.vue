<template>
  <v-container class="api-keys">
    <v-row>
      <v-col>
        <h1>API Keys</h1>
      </v-col>
    </v-row>
    <premium-settings></premium-settings>
    <exchange-settings></exchange-settings>
    <external-services></external-services>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import PremiumSettings from '@/components/settings/PremiumSettings.vue';
import ExchangeSettings from '@/components/settings/ExchangeSettings.vue';
import FiatBalances from '@/components/settings/FiatBalances.vue';
import BlockchainBalances from '@/components/settings/BlockchainBalances.vue';
import ExternalServices from '@/components/ExternalServices.vue';

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
