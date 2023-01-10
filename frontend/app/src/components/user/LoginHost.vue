<script setup lang="ts">
import ConnectionFailureMessage from '@/components/account-management/ConnectionFailureMessage.vue';
import ConnectionLoading from '@/components/account-management/ConnectionLoading.vue';
import PremiumReminder from '@/components/account-management/PremiumReminder.vue';
import BackendSettingsButton from '@/components/helper/OnboardingSettingsButton.vue';
import PrivacyNotice from '@/components/PrivacyNotice.vue';
import AboutButton from '@/components/user/AboutButton.vue';
import AnimationsButton from '@/components/user/AnimationsButton.vue';
import LoginHeader from '@/components/user/LoginHeader.vue';
import LoginIcon from '@/components/user/LoginIcon.vue';
import LoginOverlay from '@/components/user/LoginOverlay.vue';
import { useMainStore } from '@/store/main';
import DockerWarning from '@/components/account-management/DockerWarning.vue';

const css = useCssModule();

const { autolog } = useAutoLogin();
const { isPackaged } = useInterop();
const { isPremiumDialogVisible } = usePremiumReminder();
const { connectionFailure, connected, dockerRiskAccepted } = storeToRefs(
  useMainStore()
);
</script>

<template>
  <login-overlay>
    <div v-if="!isPremiumDialogVisible" :class="css.wrapper">
      <div :class="css.container">
        <v-card
          class="pb-4"
          :class="css.card"
          light
          data-cy="account-management"
        >
          <login-header />
          <docker-warning v-if="!dockerRiskAccepted && !isPackaged" />
          <connection-loading
            v-else-if="!connectionFailure"
            :connected="connected && !autolog"
          />
          <connection-failure-message v-else />
          <div
            v-if="connected && (isPackaged || dockerRiskAccepted)"
            data-cy="account-management-forms"
          >
            <router-view />
          </div>
        </v-card>
      </div>

      <login-icon left>
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

<style module lang="scss">
.container {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

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
