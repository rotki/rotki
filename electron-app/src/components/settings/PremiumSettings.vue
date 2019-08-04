<template>
  <v-layout class="premium-settings">
    <v-flex>
      <v-card>
        <v-card-title>Premium Settings</v-card-title>
        <v-card-text>
          <v-text-field
            id="premium_api_key_entry"
            v-model="apiKey"
            prepend-icon="fa-key"
            :disabled="premium && !edit"
            label="Rotkehlchen API Key"
            type="text"
          ></v-text-field>
          <v-text-field
            id="premium_api_secret_entry"
            v-model="apiSecret"
            :disabled="premium && !edit"
            prepend-icon="fa-user-secret"
            label="Rotkehlchen API Key"
            type="text"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn
            id="setup_premium_button"
            depressed
            color="primary"
            type="submit"
            :disable="premium"
            @click="setupPremium()"
          >
            {{ premium ? 'Replace Key' : 'Setup' }}
          </v-btn>
          <v-btn
            v-if="edit"
            id="premium-edit-cancel-button"
            depressed
            color="primary"
            @click="edit = false"
          >
            Cancel
          </v-btn>
          <v-switch
            v-if="premium && !edit"
            v-model="sync"
            class="premium-settings__sync"
            label="Allow data sync with Rotkehlchen Server"
            @change="onSyncChange()"
          ></v-switch>
        </v-card-actions>
      </v-card>
    </v-flex>
    <message-dialog
      :title="dialogTitle"
      :message="dialogMessage"
      :success="success"
      @dismiss="dismiss()"
    ></message-dialog>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import { NoResponseError } from '@/services/rotkehlchen_service';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';

@Component({
  components: {
    MessageDialog
  },
  computed: mapState(['premium', 'premiumSync'])
})
export default class PremiumSettings extends Vue {
  apiKey: string = '';
  apiSecret: string = '';
  sync: boolean = false;
  edit: boolean = false;

  premium!: boolean;
  premiumSync!: boolean;

  dialogTitle: string = '';
  dialogMessage: string = '';
  success: boolean = false;

  mounted() {
    this.sync = this.premiumSync;
  }

  setupPremium() {
    const apiKey = this.apiKey;
    const apiSecret = this.apiSecret;
    const hasPremium = this.premium;

    if (hasPremium && !this.edit) {
      this.edit = true;
      return;
    }

    this.$rpc
      .set_premium_credentials(apiKey, apiSecret)
      .then(() => {
        this.$store.commit('premium', true);
        this.success = true;
        this.dialogTitle = 'Premium Credentials';
        this.dialogMessage = 'Successfully set Premium Credentials';
        this.apiSecret = '';
        this.apiKey = '';
        this.edit = false;
      })
      .catch((reason: Error) => {
        this.$store.commit('premium', hasPremium);
        this.success = false;
        this.dialogTitle = 'Premium Credentials Error';
        if (reason instanceof NoResponseError) {
          this.dialogMessage =
            'Error at adding credentials for premium subscription';
        } else {
          this.dialogMessage = reason.message;
        }
      });
  }

  onSyncChange() {
    const shouldSync = this.sync;
    this.$rpc
      .set_premium_option_sync(shouldSync)
      .then(() => {
        this.$store.commit('premiumSync', shouldSync);
      })
      .catch(() => {
        this.$store.commit('premiumSync', !shouldSync);
        this.dialogTitle = 'Premium Settings Error';
        this.dialogMessage = 'Failed to change sync settings';
        this.success = false;
      })
      .finally(() => {
        if (this.sync != shouldSync) {
          this.sync = shouldSync;
        }
      });
  }

  dismiss() {
    this.dialogTitle = '';
    this.dialogMessage = '';
  }
}
</script>

<style scoped lang="scss">
.premium-settings__sync {
  margin-left: 20px;
}
</style>
