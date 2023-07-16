<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

const isDevelopment = checkIfDevelopment();

const { smAndUp } = useDisplay();

const { darkModeEnabled } = useDarkMode();
const { showPinned, showNotesSidebar, showNotificationBar, showHelpBar } =
  storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <Fragment>
    <div class="d-flex overflow-hidden">
      <SyncIndicator />
      <GlobalSearch v-if="smAndUp" />
      <BackButton />
    </div>
    <VSpacer />
    <div class="d-flex overflow-hidden fill-height align-center">
      <GetPremiumButton />
      <VBtn v-if="isDevelopment && smAndUp" to="/playground" icon>
        <VIcon>mdi-crane</VIcon>
      </VBtn>
      <AppUpdateIndicator />
      <UserNotesIndicator
        :visible="showNotesSidebar"
        @visible:update="showNotesSidebar = $event"
      />
      <PinnedIndicator
        :visible="showPinned"
        @visible:update="showPinned = $event"
      />
      <ThemeControl v-if="smAndUp" :dark-mode-enabled="darkModeEnabled" />
      <NotificationIndicator
        :visible="showNotificationBar"
        class="app__app-bar__button"
        @click="showNotificationBar = !showNotificationBar"
      />
      <CurrencyDropdown class="app__app-bar__button" />
      <PrivacyModeDropdown v-if="smAndUp" class="app__app-bar__button" />
      <UserDropdown class="app__app-bar__button" />
      <HelpIndicator
        v-if="smAndUp"
        :visible="showHelpBar"
        @visible:update="showHelpBar = $event"
      />
    </div>
  </Fragment>
</template>

<style module lang="scss">
.language {
  width: 110px;
}
</style>
