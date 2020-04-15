<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>External Services</v-card-title>
          <v-card-text>
            <p>
              Rotki can connect to service providers in order to obtain more
              details about your transactions, usually of an optional nature. In
              certain cases Rotki depends on these APIs for basic information,
              in which case you will need to provide an API key.
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <service-key
          v-model="etherscanKey"
          class="external-services__etherscan-key"
          title="Etherscan"
          description="Required for any Ethereum blockchain balances or transactions. Rotki uses etherscan to obtain basic information about ethereum blockchain addresses and transactions."
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
          description="Rotki uses cryptocompare to obtain price information about assets in your portfolio. An API key is only needed if you have a lot of assets and are being rate-limited."
          label="API key"
          hint="Enter your CryptoCompare API key"
          :loading="loading"
          tooltip="Deletes the CryptoCompare API key"
          @save="save('cryptocompare', $event)"
          @delete-key="deleteKey('cryptocompare')"
        ></service-key>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <service-key
          v-model="alethioKey"
          class="external-services__alethio-key"
          title="Alethio"
          description="Rotki uses Alethio for supplementary Ethereum blockchain information. An API key is only needed if you have a lot of assets and are being rate-limited."
          label="API key"
          hint="Enter your Alethio API key"
          :loading="loading"
          tooltip="Deletes the Alethio API key"
          @save="save('alethio', $event)"
          @delete-key="deleteKey('alethio')"
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
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { ExternalServiceKeys } from '@/model/action-result';
import { Message } from '@/store/store';
import { ExternalServiceKey, ExternalServiceName } from '@/typing/types';

@Component({
  components: { ServiceKey, ConfirmDialog, RevealableInput }
})
export default class ExternalServices extends Vue {
  etherscanKey: string = '';
  cryptocompareKey: string = '';
  alethioKey: string = '';

  serviceToDelete: ExternalServiceName | '' = '';

  loading: boolean = false;

  private updateKeys({
    cryptocompare,
    etherscan,
    alethio
  }: ExternalServiceKeys) {
    this.cryptocompareKey = cryptocompare?.api_key || '';
    this.etherscanKey = etherscan?.api_key || '';
    this.alethioKey = alethio?.api_key || '';
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
