<script setup lang="ts">
const isDevelopment = checkIfDevelopment();

const { smAndUp } = useDisplay();

const { darkModeEnabled } = useDarkMode();
const { showPinned, showNotesSidebar, showNotificationBar, showHelpBar }
  = storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <div class="flex overflow-hidden grow">
    <SyncIndicator />
    <GlobalSearch v-if="smAndUp" />
    <BackButton />
  </div>
  <div class="flex overflow-hidden h-full items-center">
    <GetPremiumButton />
    <RouterLink
      v-if="isDevelopment && smAndUp"
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
      v-model:visible="showNotesSidebar"
    />
    <PinnedIndicator
      v-model:visible="showPinned"
    />
    <ThemeControl
      v-if="smAndUp"
      :dark-mode-enabled="darkModeEnabled"
    /><NotificationIndicator
      :visible="showNotificationBar"
      class="app__app-bar__button"
      @click="showNotificationBar = !showNotificationBar"
    />
    <CurrencyDropdown class="app__app-bar__button" />
    <PrivacyModeDropdown
      v-if="smAndUp"
      class="app__app-bar__button"
    />
    <UserDropdown class="app__app-bar__button" />
    <HelpIndicator
      v-if="smAndUp"
      v-model:visible="showHelpBar"
    />
  </div>
</template>

<style module lang="scss">
.language {
  width: 110px;
}
</style>
