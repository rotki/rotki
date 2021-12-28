<template>
  <v-row class="premium-settings">
    <v-col>
      <card>
        <template #title>
          {{ $t('premium_settings.title') }}
        </template>
        <template #subtitle>
          <i18n tag="div" path="premium_settings.subtitle">
            <base-external-link
              :text="$t('premium_settings.rotki_premium')"
              :href="$interop.premiumURL"
            />
          </i18n>
        </template>

        <revealable-input
          v-model="apiKey"
          class="premium-settings__fields__api-key"
          :disabled="premium && !edit"
          :error-messages="errorMessages"
          :label="$t('premium_settings.fields.api_key')"
          @paste="onApiKeyPaste"
        />
        <revealable-input
          v-model="apiSecret"
          class="premium-settings__fields__api-secret"
          prepend-icon="mdi-lock"
          :disabled="premium && !edit"
          :label="$t('premium_settings.fields.api_secret')"
          @paste="onApiSecretPaste"
        />
        <div v-if="premium" class="premium-settings__premium-active">
          <v-icon color="success">mdi-check-circle</v-icon>
          <div>{{ $t('premium_settings.premium_active') }}</div>
        </div>

        <template #buttons>
          <v-row align="center">
            <v-col cols="auto">
              <v-btn
                class="premium-settings__button__setup"
                depressed
                color="primary"
                type="submit"
                @click="setup()"
              >
                {{
                  premium && !edit
                    ? $t('premium_settings.actions.replace')
                    : $t('premium_settings.actions.setup')
                }}
              </v-btn>
            </v-col>
            <v-col v-if="premium && !edit" cols="auto">
              <v-btn
                class="premium-settings__button__delete"
                depressed
                outlined
                color="primary"
                type="submit"
                @click="confirmDeletePremium = true"
              >
                {{ $t('premium_settings.actions.delete') }}
              </v-btn>
            </v-col>
            <v-col v-if="edit && premium" cols="auto">
              <v-btn
                id="premium-edit-cancel-button"
                depressed
                color="primary"
                @click="cancelEdit()"
              >
                {{ $t('premium_settings.actions.cancel') }}
              </v-btn>
            </v-col>
            <v-col v-if="premium && !edit" cols="auto">
              <v-switch
                v-model="sync"
                class="premium-settings__sync"
                hide-details
                :label="$t('premium_settings.actions.sync')"
                @change="onSyncChange()"
              />
            </v-col>
          </v-row>
        </template>
      </card>
    </v-col>
    <confirm-dialog
      :display="confirmDeletePremium"
      confirm-type="warning"
      :primary-action="
        $t('premium_settings.delete_confirmation.actions.delete')
      "
      :secondary-action="
        $t('premium_settings.delete_confirmation.actions.cancel')
      "
      :title="$t('premium_settings.delete_confirmation.title')"
      :message="$t('premium_settings.delete_confirmation.message')"
      @confirm="remove"
      @cancel="confirmDeletePremium = false"
    />
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { PremiumCredentialsPayload } from '@/store/session/types';
import { ActionStatus } from '@/store/types';
import { SettingsUpdate } from '@/types/user';
import { trimOnPaste } from '@/utils/event';

@Component({
  components: {
    RevealableInput,
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

  premium!: boolean;
  premiumSync!: boolean;
  username!: string;

  setupPremium!: (payload: PremiumCredentialsPayload) => Promise<ActionStatus>;
  deletePremium!: () => Promise<ActionStatus>;
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

  onApiKeyPaste(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.apiKey = paste;
    }
  }

  onApiSecretPaste(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.apiSecret = paste;
    }
  }

  mounted() {
    this.sync = this.premiumSync;
    this.edit = !this.premium && !this.edit;
  }

  cancelEdit() {
    this.edit = false;
    this.apiKey = '';
    this.apiSecret = '';
    this.clearErrors();
  }

  async setup() {
    this.clearErrors();
    if (this.premium && !this.edit) {
      this.edit = true;
      return;
    }

    const payload: PremiumCredentialsPayload = {
      username: this.username,
      apiKey: this.apiKey.trim(),
      apiSecret: this.apiSecret.trim()
    };
    const { success, message } = await this.setupPremium(payload);
    if (!success) {
      this.errorMessages.push(
        message ?? this.$tc('premium_settings.error.setting_failed')
      );
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
    const { success, message } = await this.deletePremium();
    if (!success) {
      this.errorMessages.push(
        message ?? this.$tc('premium_settings.error.removing_failed')
      );
      return;
    }
    this.$interop.premiumUserLoggedIn(false);
    this.reset();
  }

  async onSyncChange() {
    await this.updateSettings({ premiumShouldSync: this.sync });
  }
}
</script>

<style scoped lang="scss">
.premium-settings {
  &__sync {
    margin-left: 20px;
    margin-top: 0;
    padding-top: 0;
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
