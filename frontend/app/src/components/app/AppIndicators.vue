<script setup lang="ts">
import { checkIfDevelopment } from '@shared/utils';
import CurrencyDropdown from '@/components/CurrencyDropdown.vue';
import HelpIndicator from '@/components/help/HelpIndicator.vue';
import BackButton from '@/components/helper/BackButton.vue';
import UserNotesIndicator from '@/components/notes/UserNotesIndicator.vue';
import PinnedIndicator from '@/components/PinnedIndicator.vue';
import GetPremiumButton from '@/components/premium/GetPremiumButton.vue';
import PrivacyModeDropdown from '@/components/PrivacyModeDropdown.vue';
import AppUpdateIndicator from '@/components/status/AppUpdateIndicator.vue';
import NotificationIndicator from '@/components/status/NotificationIndicator.vue';
import SyncIndicator from '@/components/status/sync/SyncIndicator.vue';
import UserDropdown from '@/components/UserDropdown.vue';
import ThemeControl from '@/modules/theme/ThemeControl.vue';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import EvmQueryIndicatorToggle from './EvmQueryIndicatorToggle.vue';

const isDevelopment = checkIfDevelopment();
const isDemoMode = import.meta.env.VITE_DEMO_MODE !== undefined;

const { isSmAndUp } = useBreakpoint();

const { isDark } = useRotkiTheme();
const { showHelpBar, showNotesSidebar, showNotificationBar, showPinned } = storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <div class="flex overflow-hidden grow items-center">
    <SyncIndicator />
    <BackButton />
  </div>
  <div class="flex overflow-hidden h-full items-center">
    <GetPremiumButton hide-on-small-screen />
    <RouterLink
      v-if="isDevelopment && isSmAndUp && !isDemoMode"
      to="/playground"
    >
      <RuiButton
        variant="text"
        class="!text-rui-text-secondary"
        icon
      >
        <RuiIcon name="lu-code-xml" />
      </RuiButton>
    </RouterLink>
    <EvmQueryIndicatorToggle />
    <AppUpdateIndicator />
    <UserNotesIndicator v-model:visible="showNotesSidebar" />
    <PinnedIndicator v-model:visible="showPinned" />
    <ThemeControl
      v-if="isSmAndUp"
      :dark-mode-enabled="isDark"
    />
    <NotificationIndicator
      :visible="showNotificationBar"
      class="app__app-bar__button"
      @click="showNotificationBar = !showNotificationBar"
    />
    <CurrencyDropdown class="app__app-bar__button" />
    <PrivacyModeDropdown
      v-if="isSmAndUp"
      class="app__app-bar__button"
    />
    <UserDropdown class="app__app-bar__button" />
    <HelpIndicator
      v-if="isSmAndUp"
      v-model:visible="showHelpBar"
    />
  </div>
</template>

<style module lang="scss">
.language {
  width: 110px;
}
</style>
