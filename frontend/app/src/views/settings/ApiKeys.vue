<template>
  <v-container class="api-keys">
    <v-row>
      <v-col>
        <h1>API Keys</h1>
        <tab-navigation :tab-contents="apiKeysTabs" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';

@Component({
  components: {
    TabNavigation
  }
})
export default class ApiKeys extends Vue {
  readonly apiKeysTabs: TabContent[] = [
    {
      name: 'Rotki Premium',
      routeTo: '/settings/api-keys/rotki-premium'
    },
    {
      name: 'Exchanges',
      routeTo: '/settings/api-keys/exchanges'
    },
    {
      name: 'External Services',
      routeTo: '/settings/api-keys/external-services'
    }
  ];
}
</script>

<style scoped lang="scss">
.api-keys {
  * {
    margin-bottom: 16px;
  }
}
</style>
