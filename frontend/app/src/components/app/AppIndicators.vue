<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { checkIfDevelopment } from '@/utils/env-utils';

const isDevelopment = checkIfDevelopment();

const { currentBreakpoint } = useTheme();
const smAndUp = computed(() => get(currentBreakpoint).smAndUp);

const { darkModeEnabled } = useDarkMode();
const { showPinned, showNotesSidebar, showNotificationBar, showHelpBar } =
  storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <fragment>
    <div class="d-flex overflow-hidden">
      <sync-indicator />
      <global-search v-if="smAndUp" />
      <back-button />
    </div>
    <v-spacer />
    <div class="d-flex overflow-hidden fill-height align-center">
      <v-btn v-if="isDevelopment && smAndUp" to="/playground" icon>
        <v-icon>mdi-crane</v-icon>
      </v-btn>
      <app-update-indicator />
      <user-notes-indicator
        :visible="showNotesSidebar"
        @visible:update="showNotesSidebar = $event"
      />
      <pinned-indicator
        :visible="showPinned"
        @visible:update="showPinned = $event"
      />
      <theme-control v-if="smAndUp" :dark-mode-enabled="darkModeEnabled" />
      <notification-indicator
        :visible="showNotificationBar"
        class="app__app-bar__button"
        @click="showNotificationBar = !showNotificationBar"
      />
      <currency-dropdown class="app__app-bar__button" />
      <privacy-mode-dropdown v-if="smAndUp" class="app__app-bar__button" />
      <user-dropdown class="app__app-bar__button" />
      <help-indicator
        v-if="smAndUp"
        :visible="showHelpBar"
        @visible:update="showHelpBar = $event"
      />
    </div>
  </fragment>
</template>
<style module lang="scss">
.language {
  width: 110px;
}
</style>
