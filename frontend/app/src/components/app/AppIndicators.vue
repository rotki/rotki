<script setup lang="ts">
import { checkIfDevelopment } from '@shared/utils';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { useDarkMode } from '@/composables/dark-mode';
import HelpIndicator from '@/components/help/HelpIndicator.vue';
import UserDropdown from '@/components/UserDropdown.vue';
import PrivacyModeDropdown from '@/components/PrivacyModeDropdown.vue';
import CurrencyDropdown from '@/components/CurrencyDropdown.vue';
import NotificationIndicator from '@/components/status/NotificationIndicator.vue';
import ThemeControl from '@/components/premium/ThemeControl.vue';
import PinnedIndicator from '@/components/PinnedIndicator.vue';
import UserNotesIndicator from '@/components/notes/UserNotesIndicator.vue';
import AppUpdateIndicator from '@/components/status/AppUpdateIndicator.vue';
import GetPremiumButton from '@/components/premium/GetPremiumButton.vue';
import BackButton from '@/components/helper/BackButton.vue';
import GlobalSearch from '@/components/GlobalSearch.vue';
import SyncIndicator from '@/components/status/sync/SyncIndicator.vue';

const isDevelopment = checkIfDevelopment();

const { isSmAndUp } = useBreakpoint();

const { darkModeEnabled } = useDarkMode();
const { showHelpBar, showNotesSidebar, showNotificationBar, showPinned } = storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <div class="flex overflow-hidden grow items-center">
    <SyncIndicator />
    <GlobalSearch v-if="isSmAndUp" />
    <BackButton />
  </div>
  <div class="flex overflow-hidden h-full items-center">
    <GetPremiumButton />
    <RouterLink
      v-if="isDevelopment && isSmAndUp"
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
      :dark-mode-enabled="darkModeEnabled"
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
    <HelpIndicator
      v-if="isSmAndUp"
      v-model:visible="showHelpBar"
    />
    <UserDropdown class="app__app-bar__button" />
  </div>
</template>

<style module lang="scss">
.language {
  width: 110px;
}
</style>
