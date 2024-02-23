<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library-compat';
import Fragment from '@/components/helper/Fragment';

const isDevelopment = checkIfDevelopment();

const { isSmAndUp } = useBreakpoint();

const { darkModeEnabled } = useDarkMode();
const { showPinned, showNotesSidebar, showNotificationBar, showHelpBar }
  = storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <Fragment>
    <div class="flex overflow-hidden grow">
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
          icon
        >
          <RuiIcon name="code-box-line" />
        </RuiButton>
      </RouterLink>
      <AppUpdateIndicator />
      <UserNotesIndicator
        :visible.sync="showNotesSidebar"
      />
      <PinnedIndicator
        :visible.sync="showPinned"
      />
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
      <UserDropdown class="app__app-bar__button" />
      <HelpIndicator
        v-if="isSmAndUp"
        :visible.sync="showHelpBar"
      />
    </div>
  </Fragment>
</template>

<style module lang="scss">
.language {
  width: 110px;
}
</style>
