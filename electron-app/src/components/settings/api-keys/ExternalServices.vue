<template>
  <div>
    <v-row>
      <v-col cols="12">
        <h2>External Services</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <service-key
          v-model="etherscanKey"
          class="external-services__etherscan-key"
          title="Etherscan"
          label="API key"
          hint="Enter your Etherscan API key"
          :loading="loading"
          tooltip="Deletes the Etherscan API key"
          @save="save('etherscan', $event)"
          @delete-key="deleteKey('etherscan')"
        ></service-key>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <service-key
          v-model="cryptocompareKey"
          class="external-services__cryptocompare-key"
          title="CryptoCompare"
          label="API key"
          hint="Enter your CryptoCompare API key"
          :loading="loading"
          tooltip="Deletes the CryptoCompare API key"
          @save="save('cryptocompare', $event)"
          @delete-key="deleteKey('cryptocompare')"
        ></service-key>
      </v-col>
    </v-row>
    <confirm-dialog
      title="Delete API Key"
      message="Are you sure you want to delete this API Key?"
      :display="!!serviceToDelete"
      @confirm="confirmDelete"
      @cancel="serviceToDelete = ''"
    >
    </confirm-dialog>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { ExternalServiceKey, ExternalServiceName } from '@/typing/types';
import { Message } from '@/store/store';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { ExternalServiceKeys } from '@/model/action-result';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';

@Component({
  components: { ServiceKey, ConfirmDialog, RevealableInput }
})
export default class ExternalServices extends Vue {
  etherscanKey: string = '';
  cryptocompareKey: string = '';

  serviceToDelete: ExternalServiceName | '' = '';

  loading: boolean = false;

  private updateKeys({ cryptocompare, etherscan }: ExternalServiceKeys) {
    this.cryptocompareKey = cryptocompare?.api_key || '';
    this.etherscanKey = etherscan?.api_key || '';
  }

  async mounted() {
    this.loading = true;
    this.updateKeys(await this.$api.queryExternalServices());
    this.loading = false;
  }

  async save(serviceName: ExternalServiceName, key: string) {
    const keys: ExternalServiceKey[] = [{ name: serviceName, api_key: key }];

    try {
      this.loading = true;
      this.updateKeys(await this.$api.setExternalServices(keys));
      this.$store.commit('setMessage', {
        title: 'Success',
        description: `Successfully updated the key for ${serviceName}`,
        success: true
      } as Message);
    } catch (e) {
      this.$store.commit('setMessage', {
        title: 'Error',
        description: `Error while settings external service api keys: ${e.message}`
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

<style scoped></style>
