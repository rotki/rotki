<template>
  <v-menu
    id="balances-saved-dropdown"
    transition="slide-y-transition"
    offset-y
    bottom
    z-index="215"
  >
    <template #activator="{ on }">
      <menu-tooltip-button
        :tooltip="$tc('balances_saved_indicator.menu_tooltip', premium ? 2 : 1)"
        class-name="secondary--text text--lighten-2"
        :on-menu="on"
      >
        <v-icon>
          mdi-content-save
        </v-icon>
      </menu-tooltip-button>
    </template>
    <div class="balance-saved-indicator__content">
      <v-row v-if="displaySyncInformation">
        <v-col>
          <v-row no-gutters>
            <v-col class="font-weight-medium">
              {{ $t('balances_saved_indicator.last_data_upload') }}
            </v-col>
          </v-row>
          <v-row class="text--secondary">
            <v-col>
              <date-display v-if="lastDataUpload" :timestamp="lastDataUpload" />
              <span v-else>
                {{ $t('balances_saved_indicator.never_saved') }}
              </span>
            </v-col>
          </v-row>
        </v-col>
      </v-row>
      <v-divider v-if="displaySyncInformation" />
      <v-row>
        <v-col>
          <v-row class="font-weight-medium" no-gutters>
            <v-col>{{ $t('balances_saved_indicator.snapshot_title') }}</v-col>
          </v-row>
          <v-row class="text--secondary">
            <v-col>
              <date-display
                v-if="lastBalanceSave"
                :timestamp="lastBalanceSave"
              />
              <span v-else>
                {{ $t('balances_saved_indicator.never_saved') }}
              </span>
            </v-col>
          </v-row>
          <v-divider />
          <v-row align="center">
            <v-col>
              <v-btn color="primary" outlined @click="refreshAllAndSave()">
                <v-icon left>mdi-content-save</v-icon>
                {{ $t('balances_saved_indicator.force_save') }}
              </v-btn>
            </v-col>
            <v-col cols="auto">
              <v-tooltip bottom max-width="300px">
                <template #activator="{ on }">
                  <v-icon class="ml-3" v-on="on">mdi-information</v-icon>
                </template>
                <div>{{ $t('balances_saved_indicator.snapshot_tooltip') }}</div>
              </v-tooltip>
            </v-col>
          </v-row>
        </v-col>
      </v-row>
    </div>
  </v-menu>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import DateDisplay from '@/components/display/DateDisplay.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { AllBalancePayload } from '@/store/balances/types';

@Component({
  components: { DateDisplay, MenuTooltipButton },
  computed: {
    ...mapState('session', [
      'lastBalanceSave',
      'premiumSync',
      'lastDataUpload',
      'premium'
    ])
  }
})
export default class BalanceSavedIndicator extends Vue {
  lastBalanceSave!: number;
  premiumSync!: boolean;
  premium!: boolean;
  lastDataUpload!: string;

  get displaySyncInformation(): boolean {
    return this.premium && this.premiumSync;
  }

  refreshAllAndSave() {
    this.$store.dispatch('balances/fetchBalances', {
      ignoreCache: true,
      saveData: true
    } as AllBalancePayload);
  }
}
</script>

<style lang="scss" scoped>
.balance-saved-indicator {
  &__content {
    background: white;
    width: 280px;
    padding: 0 16px;
  }
}
</style>
