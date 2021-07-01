<template>
  <v-container class="decentralized-finance">
    <base-page-header :text="$t('decentralized_finance.title')">
      <v-tooltip v-if="defiSetupDone" top>
        <template #activator="{ on, attrs }">
          <v-btn
            text
            fab
            depressed
            v-bind="attrs"
            to="/settings/modules"
            v-on="on"
          >
            <v-icon color="primary">mdi-cog</v-icon>
          </v-btn>
        </template>
        <span>{{ $t('decentralized_finance.settings_tooltip') }}</span>
      </v-tooltip>
    </base-page-header>
    <v-row>
      <v-col>
        <div class="d-flex justify-space-between align-center" />
        <tab-navigation
          v-if="defiSetupDone"
          :tab-contents="tabs"
          no-content-margin
        />
        <defi-wizard v-else class="mt-8" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { Routes } from '@/router/routes';
import { DEFI_SETUP_DONE } from '@/store/settings/consts';

@Component({
  components: { BasePageHeader, DefiWizard, TabNavigation },
  computed: {
    ...mapState('settings', [DEFI_SETUP_DONE])
  }
})
export default class DecentralizedFinance extends Vue {
  [DEFI_SETUP_DONE]!: boolean;

  readonly tabs: TabContent[] = [
    {
      name: this.$tc('decentralized_finance.tabs.overview'),
      routeTo: Routes.DEFI_OVERVIEW
    },
    {
      name: this.$tc('decentralized_finance.tabs.deposits'),
      routeTo: Routes.DEFI_DEPOSITS
    },
    {
      name: this.$tc('decentralized_finance.tabs.liabilities'),
      routeTo: Routes.DEFI_LIABILITIES
    },
    {
      name: this.$tc('decentralized_finance.tabs.dex_trades'),
      routeTo: Routes.DEFI_DEX_TRADES
    },
    {
      name: this.$t('decentralized_finance.tabs.airdrops').toString(),
      routeTo: Routes.DEFI_AIRDROPS
    }
  ];
}
</script>

<style scoped lang="scss">
.decentralized-finance {
  height: 100%;
}
</style>
