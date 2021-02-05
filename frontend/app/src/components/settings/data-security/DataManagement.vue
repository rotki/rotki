<template>
  <v-row no-gutters>
    <v-col>
      <v-card>
        <v-card-title>
          <card-title>{{ $t('data_management.title') }}</card-title>
        </v-card-title>
        <v-card-subtitle v-text="$t('data_management.subtitle')" />
        <v-form ref="form">
          <v-card-text>
            <v-row>
              <v-col>
                <purge-selector
                  v-model="source"
                  :status="status"
                  :pending="pending"
                  @purge="showConfirmation($event)"
                />
              </v-col>
            </v-row>
          </v-card-text>
        </v-form>
      </v-card>
      <confirm-dialog
        v-if="confirm"
        display
        :title="$t('data_management.confirm.title')"
        :message="
          $t('data_management.confirm.message', { source: sourceLabel })
        "
        @confirm="purge(source)"
        @cancel="confirm = false"
      />
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import PurgeSelector, {
  ALL_TRANSACTIONS,
  ALL_MODULES,
  ALL_EXCHANGES,
  Purgable,
  PurgeParams
} from '@/components/settings/data-security/PurgeSelector.vue';
import StatusButton from '@/components/settings/data-security/StatusButton.vue';
import { SUPPORTED_EXCHANGES } from '@/data/defaults';
import { SupportedExchange } from '@/services/balances/types';
import { MODULES } from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';
import { ActionStatus } from '@/store/types';

@Component({
  components: { PurgeSelector, StatusButton, ConfirmDialog }
})
export default class DataManagement extends Vue {
  source: Purgable = ALL_TRANSACTIONS;
  status: ActionStatus | null = null;
  confirm: boolean = false;
  pending: boolean = false;
  sourceLabel: string = '';

  showConfirmation(source: PurgeParams) {
    this.sourceLabel = source.text;
    this.confirm = true;
  }

  async purge(source: string) {
    this.confirm = false;
    try {
      this.pending = true;
      await this.purgeSource(source);
      this.status = {
        message: this.$t('data_management.success', {
          source: this.sourceLabel
        }).toString(),
        success: true
      };
      setTimeout(() => (this.status = null), 5000);
    } catch (e) {
      this.status = {
        message: this.$t('data_management.error', {
          source: this.sourceLabel
        }).toString(),
        success: false
      };
    } finally {
      this.pending = false;
    }
  }

  private async purgeSource(source: string) {
    if (source === ALL_TRANSACTIONS) {
      await this.$api.balances.deleteEthereumTransactions();
    } else if (source === ALL_MODULES) {
      await this.$api.balances.deleteModuleData();
    } else if (source === ALL_EXCHANGES) {
      await this.$api.balances.deleteExchangeData();
    } else {
      if (SUPPORTED_EXCHANGES.includes(source as any)) {
        await this.$api.balances.deleteExchangeData(
          source as SupportedExchange
        );
      } else if (MODULES.includes(source as any)) {
        await this.$api.balances.deleteModuleData(source as SupportedModules);
      }
    }
  }
}
</script>
