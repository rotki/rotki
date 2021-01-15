<template>
  <fragment>
    <v-menu
      id="balances-saved-dropdown"
      transition="slide-y-transition"
      offset-y
      bottom
      z-index="215"
    >
      <template #activator="{ on }">
        <menu-tooltip-button
          :tooltip="$tc('sync_indicator.menu_tooltip', premium ? 2 : 1)"
          class-name="secondary--text text--lighten-2"
          :on-menu="on"
        >
          <v-icon> mdi-content-save </v-icon>
        </menu-tooltip-button>
      </template>
      <v-container class="balance-saved-indicator__container">
        <div class="balance-saved-indicator__content">
          <v-row v-if="premium">
            <v-col>
              <v-row no-gutters>
                <v-col class="font-weight-medium">
                  {{ $t('sync_indicator.last_data_upload') }}
                </v-col>
              </v-row>
              <v-row class="text--secondary">
                <v-col>
                  <date-display
                    v-if="lastDataUpload"
                    :timestamp="lastDataUpload"
                  />
                  <span v-else>
                    {{ $t('sync_indicator.never_saved') }}
                  </span>
                </v-col>
              </v-row>
              <v-row>
                <v-col>
                  <sync-buttons
                    :pending="pending"
                    :sync-action="syncAction"
                    @action="showConfirmation($event)"
                  />
                </v-col>
              </v-row>
            </v-col>
          </v-row>
          <v-divider v-if="premium" class="mt-2" />
          <v-row class="mt-2">
            <v-col>
              <v-row class="font-weight-medium" no-gutters>
                <v-col>{{ $t('sync_indicator.snapshot_title') }}</v-col>
              </v-row>
              <v-row class="text--secondary">
                <v-col>
                  <date-display
                    v-if="lastBalanceSave"
                    :timestamp="lastBalanceSave"
                  />
                  <span v-else>
                    {{ $t('sync_indicator.never_saved') }}
                  </span>
                </v-col>
              </v-row>
              <v-divider class="mt-2" />
              <v-row align="center" class="mt-1">
                <v-col>
                  <v-btn color="primary" outlined @click="refreshAllAndSave()">
                    <v-icon left>mdi-content-save</v-icon>
                    {{ $t('sync_indicator.force_save') }}
                  </v-btn>
                </v-col>
                <v-col cols="auto">
                  <v-tooltip bottom max-width="300px">
                    <template #activator="{ on }">
                      <v-icon class="ml-3" v-on="on">mdi-information</v-icon>
                    </template>
                    <div>
                      {{ $t('sync_indicator.snapshot_tooltip') }}
                    </div>
                  </v-tooltip>
                </v-col>
              </v-row>
            </v-col>
          </v-row>
        </div>
      </v-container>
    </v-menu>
    <confirm-dialog
      confirm-type="warning"
      :display="displayConfirmation"
      :title="$tc('sync_indicator.upload_confirmation.title', textChoice)"
      :message="message"
      :disabled="!confirmChecked"
      :primary-action="
        $tc('sync_indicator.upload_confirmation.action', textChoice)
      "
      :secondary-action="$t('sync_indicator.upload_confirmation.cancel')"
      @cancel="cancel"
      @confirm="performSync"
    >
      <div
        v-if="isDownload"
        class="font-weight-medium mt-3"
        v-text="
          $t('sync_indicator.upload_confirmation.message_download_relogin')
        "
      />
      <v-checkbox
        v-model="confirmChecked"
        :label="$t('sync_indicator.upload_confirmation.confirm_check')"
      />
    </confirm-dialog>
  </fragment>
</template>
<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import Fragment from '@/components/helper/Fragment';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import SyncButtons from '@/components/status/sync/SyncButtons.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, SyncAction } from '@/services/types-api';
import { AllBalancePayload } from '@/store/balances/types';

@Component({
  components: {
    Fragment,
    ConfirmDialog,
    SyncButtons,
    DateDisplay,
    MenuTooltipButton
  },
  computed: {
    ...mapState('session', ['lastBalanceSave', 'lastDataUpload'])
  },
  methods: {
    ...mapActions('balances', ['fetchBalances']),
    ...mapActions('session', ['forceSync'])
  }
})
export default class SyncIndicator extends Mixins(PremiumMixin) {
  pending: boolean = false;
  confirmChecked: boolean = false;
  syncAction: SyncAction = SYNC_UPLOAD;
  lastBalanceSave!: number;
  lastDataUpload!: string;
  forceSync!: (action: SyncAction) => Promise<void>;
  fetchBalances!: (payload: AllBalancePayload) => Promise<void>;
  displayConfirmation: boolean = false;

  get isDownload(): boolean {
    return this.syncAction === SYNC_DOWNLOAD;
  }

  get textChoice(): number {
    return this.syncAction === SYNC_UPLOAD ? 1 : 2;
  }

  get message(): string {
    return this.syncAction === SYNC_UPLOAD
      ? this.$tc('sync_indicator.upload_confirmation.message_upload')
      : this.$tc('sync_indicator.upload_confirmation.message_download');
  }

  async refreshAllAndSave() {
    await this.fetchBalances({
      ignoreCache: true,
      saveData: true
    });
  }

  showConfirmation(action: SyncAction) {
    this.syncAction = action;
    this.displayConfirmation = true;
  }

  performSync() {
    this.pending = true;
    this.forceSync(this.syncAction).then(() => (this.pending = false));
    this.displayConfirmation = false;
    this.confirmChecked = false;
  }

  cancel() {
    this.displayConfirmation = false;
    this.confirmChecked = false;
  }
}
</script>

<style lang="scss" scoped>
.balance-saved-indicator {
  &__container {
    background: white;
  }

  &__content {
    width: 280px;
    padding: 16px 16px;
  }
}
</style>
