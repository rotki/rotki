<template>
  <v-row no-gutters>
    <v-col>
      <card>
        <template #title>
          {{ $t('data_management.title') }}
        </template>
        <template #subtitle>
          {{ $t('data_management.subtitle') }}
        </template>

        <v-form ref="form">
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
        </v-form>
      </card>
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
import { mapActions } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import PurgeSelector, {
  PurgeParams
} from '@/components/settings/data-security/PurgeSelector.vue';
import StatusButton from '@/components/settings/data-security/StatusButton.vue';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS
} from '@/services/session/consts';
import { Purgeable } from '@/services/session/types';
import { ACTION_PURGE_CACHED_DATA } from '@/store/session/const';
import { ActionStatus } from '@/store/types';
import { SUPPORTED_EXCHANGES, SupportedExchange } from '@/types/exchanges';
import { Module } from '@/types/modules';

@Component({
  components: { PurgeSelector, StatusButton, ConfirmDialog },
  methods: {
    ...mapActions('session', [ACTION_PURGE_CACHED_DATA])
  }
})
export default class DataManagement extends Vue {
  source: Purgeable = ALL_TRANSACTIONS;
  status: ActionStatus | null = null;
  confirm: boolean = false;
  pending: boolean = false;
  sourceLabel: string = '';
  [ACTION_PURGE_CACHED_DATA]: (purgeable: Purgeable) => Promise<void>;

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
    } catch (e: any) {
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

  private async purgeSource(source: Purgeable) {
    if (source === ALL_TRANSACTIONS) {
      await this.$api.balances.deleteEthereumTransactions();
    } else if (source === ALL_MODULES) {
      await this.$api.balances.deleteModuleData();
    } else if (source === ALL_CENTRALIZED_EXCHANGES) {
      await this.$api.balances.deleteExchangeData();
    } else if (source === ALL_DECENTRALIZED_EXCHANGES) {
      await Promise.all([
        this.$api.balances.deleteModuleData(Module.UNISWAP),
        this.$api.balances.deleteModuleData(Module.BALANCER)
      ]);
    } else {
      if (
        SUPPORTED_EXCHANGES.includes(source as any) ||
        EXTERNAL_EXCHANGES.includes(source as any)
      ) {
        await this.$api.balances.deleteExchangeData(
          source as SupportedExchange
        );
      } else if (Object.values(Module).includes(source as any)) {
        await this.$api.balances.deleteModuleData(source as Module);
      }
    }
    await this[ACTION_PURGE_CACHED_DATA](source);
  }
}
</script>
