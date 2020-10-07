<template>
  <v-container class="api-keys">
    <base-page-header :text="$t('api_keys.title')" />
    <v-row>
      <v-col>
        <tab-navigation :tab-contents="apiKeysTabs" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';

@Component({
  components: {
    BasePageHeader,
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
