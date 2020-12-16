<template>
  <v-container>
    <v-card>
      <v-card-title v-text="$t('external_services.title')" />
      <v-card-subtitle v-text="$t('external_services.subtitle')" />
      <v-card-text>
        <v-row no-gutters>
          <v-col cols="12">
            <service-key
              v-model="etherscanKey"
              class="external-services__etherscan-key"
              :title="$t('external_services.etherscan.title')"
              :description="$t('external_services.etherscan.description')"
              :label="$t('external_services.etherscan.label')"
              :hint="$t('external_services.etherscan.hint')"
              :loading="loading"
              :tooltip="$t('external_services.etherscan.delete_tooltip')"
              @save="save('etherscan', $event)"
              @delete-key="deleteKey('etherscan')"
            />
          </v-col>
        </v-row>
        <v-divider class="mt-3" />
        <v-row no-gutters>
          <v-col cols="12">
            <service-key
              v-model="cryptocompareKey"
              class="external-services__cryptocompare-key"
              :title="$t('external_services.cryptocompare.title')"
              :description="$t('external_services.cryptocompare.description')"
              :label="$t('external_services.cryptocompare.label')"
              :hint="$t('external_services.cryptocompare.hint')"
              :loading="loading"
              :tooltip="$t('external_services.cryptocompare.delete_tooltip')"
              @save="save('cryptocompare', $event)"
              @delete-key="deleteKey('cryptocompare')"
            />
          </v-col>
        </v-row>
        <v-divider class="mt-3" />
        <v-row no-gutters>
          <v-col cols="12">
            <service-key
              v-model="beaconchainKey"
              class="external-services__beaconchain-key"
              :title="$t('external_services.beaconchain.title')"
              :description="$t('external_services.beaconchain.description')"
              :label="$t('external_services.beaconchain.label')"
              :hint="$t('external_services.beaconchain.hint')"
              :loading="loading"
              :tooltip="$t('external_services.beaconchain.delete_tooltip')"
              @save="save('beaconchain', $event)"
              @delete-key="deleteKey('beaconchain')"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <confirm-dialog
      :title="$t('external_services.confirmation.title')"
      :message="$t('external_services.confirmation.message')"
      :display="!!serviceToDelete"
      @confirm="confirmDelete"
      @cancel="serviceToDelete = ''"
    />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { ExternalServiceKeys } from '@/model/action-result';
import { Message } from '@/store/types';
import { ExternalServiceKey, ExternalServiceName } from '@/typing/types';

@Component({
  components: { ServiceKey, ConfirmDialog }
})
export default class ExternalServices extends Vue {
  etherscanKey: string = '';
  cryptocompareKey: string = '';
  beaconchainKey: string = '';

  serviceToDelete: ExternalServiceName | '' = '';

  loading: boolean = false;

  private updateKeys({
    cryptocompare,
    etherscan,
    beaconchain
  }: ExternalServiceKeys) {
    this.cryptocompareKey = cryptocompare?.api_key || '';
    this.etherscanKey = etherscan?.api_key || '';
    this.beaconchainKey = beaconchain?.api_key || '';
  }

  async mounted() {
    this.loading = true;
    this.updateKeys(await this.$api.queryExternalServices());
    this.loading = false;
  }

  async save(serviceName: ExternalServiceName, key: string) {
    const keys: ExternalServiceKey[] = [
      { name: serviceName, api_key: key.trim() }
    ];

    try {
      this.loading = true;
      this.updateKeys(await this.$api.setExternalServices(keys));
      this.$store.commit('setMessage', {
        title: this.$t('external_services.set.success.title').toString(),
        description: this.$t('external_services.set.success.message', {
          serviceName
        }).toString(),
        success: true
      } as Message);
    } catch (e) {
      this.$store.commit('setMessage', {
        title: this.$t('external_services.set.error.title').toString(),
        description: this.$t('external_services.set.error.message', {
          error: e.message
        }).toString()
      } as Message);
    }
    this.loading = false;
  }

  deleteKey(serviceName: ExternalServiceName) {
    this.serviceToDelete = serviceName;
  }

  async confirmDelete() {
    /* istanbul ignore if */
    if (!this.serviceToDelete) {
      return;
    }
    try {
      this.loading = true;
      this.updateKeys(
        await this.$api.deleteExternalServices(this.serviceToDelete)
      );
    } catch (e) {
      this.$store.commit('setMessage', {
        title: 'Error',
        description: `Error while removing the external service api keys: ${e.message}`
      } as Message);
    }
    this.loading = false;
    this.serviceToDelete = '';
  }
}
</script>
