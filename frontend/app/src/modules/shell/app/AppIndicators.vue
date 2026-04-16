<script setup lang="ts">
import { checkIfDevelopment } from '@shared/utils';
import CurrencyDropdown from '@/modules/assets/amount-display/CurrencyDropdown.vue';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import UserNotesIndicator from '@/modules/notes/UserNotesIndicator.vue';
import GetPremiumButton from '@/modules/premium/GetPremiumButton.vue';
import PrivacyModeDropdown from '@/modules/settings/PrivacyModeDropdown.vue';
import AppUpdateIndicator from '@/modules/shell/components/AppUpdateIndicator.vue';
import BackButton from '@/modules/shell/components/BackButton.vue';
import HelpIndicator from '@/modules/shell/components/HelpIndicator.vue';
import PinnedIndicator from '@/modules/shell/components/navigation/PinnedIndicator.vue';
import NotificationIndicator from '@/modules/shell/components/NotificationIndicator.vue';
import UserDropdown from '@/modules/shell/components/UserDropdown.vue';
import SyncIndicator from '@/modules/shell/sync-progress/SyncIndicator.vue';
import ThemeControl from '@/modules/shell/theme/ThemeControl.vue';

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
