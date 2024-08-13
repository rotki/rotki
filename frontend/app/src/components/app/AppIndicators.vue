<script setup lang="ts">
const isDevelopment = checkIfDevelopment();

const { isSmAndUp } = useBreakpoint();

const { darkModeEnabled } = useDarkMode();
const { showPinned, showNotesSidebar, showNotificationBar, showHelpBar } = storeToRefs(useAreaVisibilityStore());
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
        <RuiIcon name="code-box-line" />
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
