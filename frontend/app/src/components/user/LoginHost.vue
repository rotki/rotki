<template>
  <login-overlay>
    <div v-if="!isPremiumDialogVisible" :class="css.wrapper">
      <v-card class="pb-4" :class="css.card" light data-cy="account-management">
        <login-header />
        <connection-loading
          v-if="!hasConnectionFailed"
          :connected="connected && !autolog"
        />
        <connection-failure v-else />
        <div v-if="connected" data-cy="account-management-forms">
          <router-view />
        </div>
      </v-card>
      <login-icon>
        <animations-button />
      </login-icon>
      <privacy-notice />
      <login-icon>
        <template v-if="isPackaged">
          <backend-settings-button />
        </template>
        <template v-else>
          <about-button />
        </template>
      </login-icon>
    </div>

    <premium-reminder v-else />
  </login-overlay>
</template>

<script setup lang="ts">
import ConnectionFailure from '@/components/account-management/ConnectionFailure.vue';
import ConnectionLoading from '@/components/account-management/ConnectionLoading.vue';
import PremiumReminder from '@/components/account-management/PremiumReminder.vue';
import BackendSettingsButton from '@/components/helper/OnboardingSettingsButton.vue';
import PrivacyNotice from '@/components/PrivacyNotice.vue';
import AboutButton from '@/components/user/AboutButton.vue';
import AnimationsButton from '@/components/user/AnimationsButton.vue';
import LoginHeader from '@/components/user/LoginHeader.vue';
import LoginIcon from '@/components/user/LoginIcon.vue';
import LoginOverlay from '@/components/user/LoginOverlay.vue';
import { useBackendManagement } from '@/composables/backend';
import { usePremiumReminder } from '@/composables/premium';
import { useInterop } from '@/electron-interop';
import { useMainStore } from '@/store/main';
import { useSessionStore } from '@/store/session';
import { useSessionAuthStore } from '@/store/session/auth';

const autolog = ref(false);

const css = useCssModule();

const { login } = useSessionStore();
const { logged } = storeToRefs(useSessionAuthStore());
const { connectionFailure: hasConnectionFailed, connected } = storeToRefs(
  useMainStore()
);
const { showGetPremiumButton, showPremiumDialog, isPremiumDialogVisible } =
  usePremiumReminder();
const { resetSessionBackend } = useBackendManagement();

onMounted(async () => {
  await resetSessionBackend();

  set(autolog, true);

  await login({ username: '', password: '' });

  if (get(logged)) {
    showPremiumDialog();
    showGetPremiumButton();
  }

  set(autolog, false);
});

const { isPackaged } = useInterop();
</script>

<style module lang="scss">
.wrapper {
  width: 600px;
  max-width: 100%;
  padding: 32px 16px 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100vh;

  @media (max-height: 800px) {
    padding-top: 0;
  }
}

.card {
  z-index: 5;
  max-height: calc(100vh - 140px);
  overflow: auto;
}
</style>
