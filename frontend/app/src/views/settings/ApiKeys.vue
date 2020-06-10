<template>
  <v-container class="api-keys">
    <v-row>
      <v-col>
        <h1>API Keys</h1>
        <tab-navigation :tab-contents="apiKeysTabs"></tab-navigation>
      </v-col>
    </v-row>
    <v-slide-x-transition>
      <router-view />
    </v-slide-x-transition>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import BlockchainBalances from '@/components/accounts/BlockchainBalances.vue';
import FiatBalances from '@/components/accounts/FiatBalances.vue';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import ExchangeSettings from '@/components/settings/api-keys/ExchangeSettings.vue';
import ExternalServices from '@/components/settings/api-keys/ExternalServices.vue';
import PremiumSettings from '@/components/settings/PremiumSettings.vue';

@Component({
  components: {
    BlockchainBalances,
    FiatBalances,
    ExchangeSettings,
    ExternalServices,
    PremiumSettings,
    TabNavigation
  }
})
export default class ApiKeys extends Vue {
  apiKeysTabs = [
    {
      name: 'Rotki Premium',
      routerTo: '/settings/api-keys/rotki-premium'
    },
    {
      name: 'Exchanges',
      routerTo: '/settings/api-keys/exchanges'
    },
    {
      name: 'External Services',
      routerTo: '/settings/api-keys/external-services'
    }
  ];
}
</script>

<style scoped lang="scss">
.api-keys > * {
  margin-bottom: 16px;
}
</style>
