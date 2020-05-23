<template>
  <v-menu
    id="balances-saved-dropdown"
    transition="slide-y-transition"
    bottom
    z-index="105"
  >
    <template #activator="{ on }">
      <v-btn color="primary" dark icon text v-on="on">
        <v-icon>
          fa fa-save
        </v-icon>
      </v-btn>
    </template>
    <div class="balance-saved-indicator__content">
      <v-row>
        Balances last saved
      </v-row>
      <v-row class="text--secondary">
        <span v-if="lastBalanceSave">
          {{ lastBalanceSave | formatDate(dateDisplayFormat) }}
        </span>
        <span v-else>
          Never
        </span>
      </v-row>
      <v-divider></v-divider>
      <v-row>
        <v-btn color="primary" outlined @click="refreshAllAndSave()">
          <v-icon left>fa fa-save</v-icon>force save
        </v-btn>
        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-icon class="ml-3" v-on="on">fa fa-info-circle</v-icon>
          </template>
          <div>
            This will refresh all balances, ignore cache, and save your
            balances.<br />
            Use this very sparingly as it may lead to you being rate-limited.
          </div>
        </v-tooltip>
      </v-row>
    </div>
  </v-menu>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { AllBalancePayload } from '@/store/balances/actions';

const { mapGetters } = createNamespacedHelpers('session');

@Component({
  computed: {
    ...mapGetters(['lastBalanceSave', 'dateDisplayFormat'])
  }
})
export default class BalanceSavedIndicator extends Vue {
  lastBalanceSave!: number;
  dateDisplayFormat!: string;

  refreshAllAndSave() {
    this.$store.dispatch('balances/fetchBalances', {
      ignoreCache: true,
      saveData: true
    } as AllBalancePayload);
  }
}
</script>

<style lang="scss" scoped>
.balance-saved-indicator__content {
  background: white;
  width: 280px;
  padding: 16px;
}

.balance-saved-indicator__content > * {
  padding: 4px 16px;
}
</style>
