<template>
  <v-row class="premium-settings">
    <v-col>
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
            :disabled="!apiKey && !apiSecret"
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
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { Message } from '@/store/store';

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

    const { commit } = this.$store;

    this.$rpc
      .set_premium_credentials(apiKey, apiSecret)
      .then(() => {
        commit('premium', true);
        commit('setMessage', {
          title: 'Premium Credentials',
          description: 'Successfully set Premium Credentials',
          success: true
        } as Message);
        this.apiSecret = '';
        this.apiKey = '';
        this.edit = false;
      })
      .catch((reason: Error) => {
        commit('premium', hasPremium);
        commit('setMessage', {
          title: 'Premium Credentials Error',
          description:
            reason.message ||
            'Error at adding credentials for premium subscription',
          success: false
        } as Message);
      });
  }

  onSyncChange() {
    const { commit } = this.$store;
    const shouldSync = this.sync;
    this.$rpc
      .set_premium_option_sync(shouldSync)
      .then(() => {
        commit('premiumSync', shouldSync);
      })
      .catch(() => {
        commit('premiumSync', !shouldSync);
        commit('setMessage', {
          title: 'Premium Settings Error',
          description: 'Failed to change sync settings',
          success: false
        });
        this.sync = !shouldSync;
      });
  }
}
</script>

<style scoped lang="scss">
.premium-settings__sync {
  margin-left: 20px;
}
</style>
