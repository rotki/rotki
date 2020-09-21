<template>
  <v-container>
    <v-row>
      <v-col>
        <div class="d-flex justify-space-between align-center text-h4">
          {{ $t('decentralized_finance.title') }}
          <v-tooltip v-if="defiSetupDone" top>
            <template #activator="{ on, attrs }">
              <v-btn
                text
                fab
                depressed
                v-bind="attrs"
                to="/settings/defi"
                v-on="on"
              >
                <v-icon color="primary">mdi-cog</v-icon>
              </v-btn>
            </template>
            <span>{{ $t('decentralized_finance.settings_tooltip') }}</span>
          </v-tooltip>
        </div>
        <tab-navigation v-if="defiSetupDone" :tab-contents="tabs" />
        <defi-wizard v-else class="mt-8" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { DEFI_SETUP_DONE } from '@/store/settings/consts';

@Component({
  components: { DefiWizard, TabNavigation },
  computed: {
    ...mapState('settings', [DEFI_SETUP_DONE])
  }
})
export default class DecentralizedFinance extends Vue {
  [DEFI_SETUP_DONE]!: boolean;

  readonly tabs: TabContent[] = [
    {
      name: this.$tc('decentralized_finance.tabs.overview'),
      routeTo: '/defi/overview'
    },
    {
      name: this.$tc('decentralized_finance.tabs.deposits'),
      routeTo: '/defi/deposits'
    },
    {
      name: this.$tc('decentralized_finance.tabs.liabilities'),
      routeTo: '/defi/liabilities'
    }
  ];
}
</script>

<style scoped></style>
