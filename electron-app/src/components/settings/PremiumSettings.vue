<template>
  <v-row class="premium-settings">
    <v-col>
      <v-card>
        <v-card-title>Rotki Premium</v-card-title>
        <v-card-text>
          <p>
            Rotki Premium is an optional subscription service to gain access to
            analytics, graphs, and unlock many additional features. For more
            information on what is available visit the
            <base-external-link :href="$interop.premiumURL">
              Rotki Premium
            </base-external-link>
            website.
          </p>
          <v-text-field
            v-model="apiKey"
            class="premium-settings__fields__api-key"
            :append-icon="edit ? (showKey ? 'fa-eye' : 'fa-eye-slash') : ''"
            prepend-icon="fa-key"
            :disabled="premium && !edit"
            :type="showKey ? 'text' : 'password'"
            label="Rotki API Key"
            @click:append="showKey = !showKey"
          ></v-text-field>
          <v-text-field
            v-model="apiSecret"
            class="premium-settings__fields__api-secret"
            :append-icon="edit ? (showSecret ? 'fa-eye' : 'fa-eye-slash') : ''"
            :disabled="premium && !edit"
            prepend-icon="fa-user-secret"
            :type="showSecret ? 'text' : 'password'"
            label="Rotki API Secret"
            @click:append="showSecret = !showSecret"
          ></v-text-field>
          <div v-if="premium" class="premium-settings__premium-active">
            <v-icon color="success">fa-check-circle</v-icon>
            <div>Rotkehlchen Premium is active</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn
            class="premium-settings__button__setup"
            depressed
            color="primary"
            type="submit"
            @click="setupPremium()"
          >
            {{ premium && !edit ? 'Replace Key' : 'Setup' }}
          </v-btn>
          <v-btn
            v-if="premium"
            class="premium-settings__button__setup"
            depressed
            outlined
            color="primary"
            type="submit"
            @click="confirmDeletePremium = true"
          >
            Delete Key
          </v-btn>
          <v-btn
            v-if="edit && premium"
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
    </v-col>
    <confirm-dialog
      :display="confirmDeletePremium"
      confirm-type="warning"
      primary-action="Delete"
      title="Delete rotki premium keys?"
      message="Are you sure you want to delete your rotki premium keys? Premium will be disabled for this session and if you want to re-enable premium you will have to enter your keys again."
      @confirm="deletePremium()"
      @cancel="confirmDeletePremium = false"
    ></confirm-dialog>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { Message } from '@/store/store';

const { mapState } = createNamespacedHelpers('session');

@Component({
  components: {
    ConfirmDialog,
    MessageDialog,
    BaseExternalLink
  },
  computed: mapState(['premium', 'premiumSync', 'username'])
})
export default class PremiumSettings extends Vue {
  apiKey: string = '';
  apiSecret: string = '';
  sync: boolean = false;
  edit: boolean = true;
  confirmDeletePremium: boolean = false;

  showKey: boolean = false;
  showSecret: boolean = false;

  premium!: boolean;
  premiumSync!: boolean;
  username!: string;

  mounted() {
    this.sync = this.premiumSync;
    if (!this.premium && !this.edit) {
      this.edit = true;
    } else {
      this.edit = false;
    }
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

    this.$api
      .setPremiumCredentials(this.username, apiKey, apiSecret)
      .then(() => {
        commit('session/premium', true);
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
        commit('session/premium', hasPremium);
        commit('setMessage', {
          title: 'Premium Credentials Error',
          description:
            reason.message ||
            'Error at adding credentials for premium subscription',
          success: false
        } as Message);
      });
  }

  deletePremium() {
    this.confirmDeletePremium = false;
    if (this.premium) {
      const { commit } = this.$store;

      this.$api
        .deletePremiumCredentials(this.username)
        .then(() => {
          commit('session/premium', false);
          commit('setMessage', {
            title: 'Premium Credentials',
            description: 'Successfully deleted premium credentials',
            success: true
          } as Message);
          this.apiSecret = '';
          this.apiKey = '';
          this.edit = false;
        })
        .catch((reason: Error) => {
          commit('session/premium', false);
          commit('setMessage', {
            title: 'Premium Credentials Error',
            description: reason.message || 'Error deleting premium credentials',
            success: false
          } as Message);
        });
    }
  }

  onSyncChange() {
    const { commit } = this.$store;
    const shouldSync = this.sync;
    this.$api
      .setPremiumSync(shouldSync)
      .then(() => {
        commit('session/premiumSync', shouldSync);
      })
      .catch(() => {
        commit('session/premiumSync', !shouldSync);
        commit('setMessage', {
          title: 'Premium Settings Error',
          description: 'Failed to change sync settings',
          success: false
        } as Message);
        this.sync = !shouldSync;
      });
  }
}
</script>

<style scoped lang="scss">
.premium-settings__sync {
  margin-left: 20px;
}

.premium-settings__premium-active {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
}

.premium-settings__premium-active div {
  margin-left: 10px;
}
</style>
