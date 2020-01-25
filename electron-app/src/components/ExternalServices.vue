<template>
  <div>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            External Services
          </v-card-title>
          <v-card-text>
            <v-row align="center">
              <v-col cols="11">
                <revealable-input
                  v-model="etherscanKey"
                  class="external-services__etherscan-key"
                  label="Etherscan API Key"
                ></revealable-input>
              </v-col>
              <v-col cols="1">
                <v-tooltip top>
                  <template #activator="{ on }">
                    <v-btn
                      icon
                      text
                      class="external-services__buttons__delete-etherscan"
                      :disabled="loading || !etherscanKey"
                      color="primary"
                      v-on="on"
                      @click="deleteKey('etherscan')"
                    >
                      <v-icon>fa-trash</v-icon>
                    </v-btn>
                  </template>
                  <span>Deletes the Etherscan API key</span>
                </v-tooltip>
              </v-col>
            </v-row>
            <v-row align="center">
              <v-col cols="11">
                <revealable-input
                  v-model="cryptocompareKey"
                  class="external-services__cryptocompare-key"
                  label="Cryptocompare API Key"
                ></revealable-input>
              </v-col>
              <v-col cols="1">
                <v-tooltip top>
                  <template #activator="{ on }">
                    <v-btn
                      class="external-services__buttons__delete-cryptocompare"
                      icon
                      text
                      :disabled="loading || !cryptocompareKey"
                      color="primary"
                      v-on="on"
                      @click="deleteKey('cryptocompare')"
                    >
                      <v-icon>fa-trash</v-icon>
                    </v-btn>
                  </template>
                  <span>Deletes the CryptoCompare API key</span>
                </v-tooltip>
              </v-col>
            </v-row>
          </v-card-text>
          <v-card-actions>
            <v-btn
              class="external-services__buttons__save"
              depressed
              color="primary"
              :disabled="
                (etherscanKey === '' && cryptocompareKey === '') || loading
              "
              @click="save()"
            >
              Save
            </v-btn>
          </v-card-actions>
        </v-card>
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

@Component({
  components: { ConfirmDialog, RevealableInput }
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

  async save() {
    const keys: ExternalServiceKey[] = [];
    if (this.cryptocompareKey) {
      keys.push({ name: 'cryptocompare', api_key: this.cryptocompareKey });
    }
    if (this.etherscanKey) {
      keys.push({ name: 'etherscan', api_key: this.etherscanKey });
    }
    try {
      this.loading = true;
      this.updateKeys(await this.$api.setExternalServices(keys));
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
