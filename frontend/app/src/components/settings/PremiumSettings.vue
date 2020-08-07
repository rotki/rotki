<template>
  <v-container>
    <v-row class="premium-settings">
      <v-col>
        <v-card>
          <v-card-title>Rotki Premium</v-card-title>
          <v-card-text>
            <p>
              Rotki Premium is an optional subscription service to gain access
              to to analytics, graphs, and unlock many additional features. For
              information on what is available visit the
              <base-external-link
                text="Rotki Premium"
                :href="$interop.premiumURL"
              ></base-external-link>
              website.
            </p>
            <v-text-field
              v-model="apiKey"
              class="premium-settings__fields__api-key"
              :append-icon="edit ? (showKey ? 'fa-eye' : 'fa-eye-slash') : ''"
              prepend-icon="fa-key"
              :disabled="premium && !edit"
              :type="showKey ? 'text' : 'password'"
              :error-messages="errorMessages"
              label="Rotki API Key"
              @click:append="showKey = !showKey"
            ></v-text-field>
            <v-text-field
              v-model="apiSecret"
              class="premium-settings__fields__api-secret"
              :append-icon="
                edit ? (showSecret ? 'fa-eye' : 'fa-eye-slash') : ''
              "
              :disabled="premium && !edit"
              prepend-icon="fa-user-secret"
              :type="showSecret ? 'text' : 'password'"
              label="Rotki API Secret"
              @click:append="showSecret = !showSecret"
            ></v-text-field>
            <div v-if="premium" class="premium-settings__premium-active">
              <v-icon color="success">fa-check-circle</v-icon>
              <div>Rotki Premium is active</div>
            </div>
          </v-card-text>
          <v-card-actions>
            <v-btn
              class="premium-settings__button__setup"
              depressed
              color="primary"
              type="submit"
              @click="setup()"
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
              label="Allow data sync with Rotki Server"
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
        message="Are you sure you want to delete the rotki premium keys for your account? If you want to re-enable premium you will have to enter your keys again."
        @confirm="remove()"
        @cancel="confirmDeletePremium = false"
      ></confirm-dialog>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { PremiumCredentialsPayload } from '@/store/session/types';
import { ActionStatus } from '@/store/types';
import { SettingsUpdate } from '@/typing/types';

@Component({
  components: {
    ConfirmDialog,
    BaseExternalLink
  },
  computed: mapState('session', ['premium', 'premiumSync', 'username']),
  methods: {
    ...mapActions('session', [
      'setupPremium',
      'deletePremium',
      'updateSettings'
    ])
  }
})
export default class PremiumSettings extends Vue {
  apiKey: string = '';
  apiSecret: string = '';
  sync: boolean = false;
  edit: boolean = true;
  confirmDeletePremium: boolean = false;
  errorMessages: string[] = [];

  showKey: boolean = false;
  showSecret: boolean = false;

  premium!: boolean;
  premiumSync!: boolean;
  username!: string;

  setupPremium!: (payload: PremiumCredentialsPayload) => Promise<ActionStatus>;
  deletePremium!: (username: string) => Promise<ActionStatus>;
  updateSettings!: (settings: SettingsUpdate) => Promise<void>;

  private reset() {
    this.apiSecret = '';
    this.apiKey = '';
    this.edit = false;
  }

  private clearErrors() {
    for (let i = 0; i < this.errorMessages.length; i++) {
      this.errorMessages.pop();
    }
  }

  mounted() {
    this.sync = this.premiumSync;
    this.edit = !this.premium && !this.edit;
  }

  async setup() {
    this.clearErrors();
    if (this.premium && !this.edit) {
      this.edit = true;
      return;
    }

    const payload: PremiumCredentialsPayload = {
      username: this.username,
      apiKey: this.apiKey,
      apiSecret: this.apiSecret
    };
    const { success, message } = await this.setupPremium(payload);
    if (!success) {
      this.errorMessages.push(message ?? 'Setting the keys was not successful');
      return;
    }
    this.$interop.premiumUserLoggedIn(true);
    this.reset();
  }

  async remove() {
    this.clearErrors();
    this.confirmDeletePremium = false;
    if (!this.premium) {
      return;
    }
    const { success, message } = await this.deletePremium(this.username);
    if (!success) {
      this.errorMessages.push(
        message ?? 'Deleting the keys was not successful'
      );
      return;
    }
    this.$interop.premiumUserLoggedIn(false);
    this.reset();
  }

  async onSyncChange() {
    await this.updateSettings({ premium_should_sync: this.sync });
  }
}
</script>

<style scoped lang="scss">
.premium-settings {
  &__sync {
    margin-left: 20px;
  }

  &__premium-active {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;

    div {
      margin-left: 10px;
    }
  }
}
</style>
