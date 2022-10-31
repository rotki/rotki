<template>
  <v-row class="premium-settings">
    <v-col>
      <card>
        <template #title>
          {{ t('premium_settings.title') }}
        </template>
        <template #subtitle>
          <i18n tag="div" path="premium_settings.subtitle">
            <base-external-link
              :text="tc('premium_settings.rotki_premium')"
              :href="premiumURL"
            />
          </i18n>
        </template>

        <revealable-input
          v-model="apiKey"
          outlined
          class="premium-settings__fields__api-key"
          :disabled="premium && !edit"
          :error-messages="errorMessages"
          :label="tc('premium_settings.fields.api_key')"
          @paste="onApiKeyPaste"
        />
        <revealable-input
          v-model="apiSecret"
          outlined
          class="premium-settings__fields__api-secret"
          prepend-icon="mdi-lock"
          :disabled="premium && !edit"
          :label="tc('premium_settings.fields.api_secret')"
          @paste="onApiSecretPaste"
        />
        <div v-if="premium" class="premium-settings__premium-active">
          <v-icon color="success">mdi-check-circle</v-icon>
          <div>{{ t('premium_settings.premium_active') }}</div>
        </div>

        <template #buttons>
          <v-row align="center">
            <v-col cols="auto">
              <v-btn
                class="premium-settings__button__setup"
                depressed
                color="primary"
                type="submit"
                @click="setupPremium()"
              >
                {{
                  premium && !edit
                    ? t('premium_settings.actions.replace')
                    : t('premium_settings.actions.setup')
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
                {{ t('premium_settings.actions.delete') }}
              </v-btn>
            </v-col>
            <v-col v-if="edit && premium" cols="auto">
              <v-btn
                id="premium-edit-cancel-button"
                depressed
                color="primary"
                @click="cancelEdit()"
              >
                {{ t('common.actions.cancel') }}
              </v-btn>
            </v-col>
            <v-col v-if="premium && !edit" cols="auto">
              <v-switch
                v-model="sync"
                class="premium-settings__sync"
                hide-details
                :label="t('premium_settings.actions.sync')"
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
      :primary-action="tc('common.actions.delete')"
      :secondary-action="tc('common.actions.cancel')"
      :title="tc('premium_settings.delete_confirmation.title')"
      :message="tc('premium_settings.delete_confirmation.message')"
      @confirm="remove"
      @cancel="confirmDeletePremium = false"
    />
  </v-row>
</template>

<script setup lang="ts">
import { Ref } from 'vue';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { useInterop } from '@/electron-interop';
import { useSessionStore } from '@/store/session';
import { usePremiumStore } from '@/store/session/premium';
import { PremiumCredentialsPayload } from '@/store/session/types';
import { useSettingsStore } from '@/store/settings';
import { trimOnPaste } from '@/utils/event';

const { username } = storeToRefs(useSessionStore());
const { update } = useSettingsStore();
const store = usePremiumStore();
const { premium, premiumSync } = storeToRefs(store);
const { setup, deletePremium } = store;

const { t, tc } = useI18n();

const { premiumURL, premiumUserLoggedIn } = useInterop();

const apiKey: Ref<string> = ref('');
const apiSecret: Ref<string> = ref('');
const sync: Ref<boolean> = ref(false);
const edit: Ref<boolean> = ref(true);
const confirmDeletePremium: Ref<boolean> = ref(false);
const errorMessages: Ref<string[]> = ref([]);

const clearErrors = () => {
  set(errorMessages, []);
};

const onApiKeyPaste = (event: ClipboardEvent) => {
  const paste = trimOnPaste(event);
  if (paste) {
    set(apiKey, paste);
  }
};

const onApiSecretPaste = (event: ClipboardEvent) => {
  const paste = trimOnPaste(event);
  if (paste) {
    set(apiSecret, paste);
  }
};

const onSyncChange = async () => {
  await update({ premiumShouldSync: get(sync) });
};

const cancelEdit = () => {
  set(edit, false);
  set(apiKey, '');
  set(apiSecret, '');
  clearErrors();
};

const reset = () => {
  set(apiSecret, '');
  set(apiKey, '');
  set(edit, false);
};

const setupPremium = async () => {
  clearErrors();
  if (get(premium) && !get(edit)) {
    set(edit, true);
    return;
  }

  const payload: PremiumCredentialsPayload = {
    username: get(username),
    apiKey: get(apiKey).trim(),
    apiSecret: get(apiSecret).trim()
  };
  const result = await setup(payload);
  if (!result.success) {
    set(errorMessages, [
      ...get(errorMessages),
      result.message ?? tc('premium_settings.error.setting_failed')
    ]);
    return;
  }
  premiumUserLoggedIn(true);
  reset();
};

const remove = async () => {
  clearErrors();
  set(confirmDeletePremium, false);
  if (!get(premium)) {
    return;
  }
  const result = await deletePremium();
  if (!result.success) {
    set(errorMessages, [
      ...get(errorMessages),
      result.message ?? tc('premium_settings.error.removing_failed')
    ]);
    return;
  }
  premiumUserLoggedIn(false);
  reset();
};

onMounted(() => {
  set(sync, get(premiumSync));
  set(edit, !get(premium) && !get(edit));
});
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
