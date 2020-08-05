<template>
  <v-container>
    <v-row>
      <v-col>
        <h1 class="d-flex justify-space-between align-center">
          Decentralized Finance
          <v-tooltip top>
            <template #activator="{ on, attrs }">
              <v-btn
                v-if="defiSetupDone"
                text
                fab
                depressed
                v-bind="attrs"
                to="/settings/defi"
                v-on="on"
              >
                <v-icon color="primary">fa-gear</v-icon>
              </v-btn>
            </template>
            <span>Opens the Defi settings</span>
          </v-tooltip>
        </h1>
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

@Component({
  components: { DefiWizard, TabNavigation },
  computed: {
    ...mapState('session', ['defiSetupDone'])
  }
})
export default class DecentralizedFinance extends Vue {
  defiSetupDone!: boolean;

  readonly tabs: TabContent[] = [
    {
      name: 'Overview',
      routeTo: '/defi/overview'
    },
    {
      name: 'Lending',
      routeTo: '/defi/lending'
    },
    {
      name: 'Borrowing',
      routeTo: '/defi/borrowing'
    }
  ];
}
</script>

<style scoped></style>
