<script setup lang="ts">
import { useAreaVisibilityStore } from '@/store/session/visibility';

const { showAbout, showHelpBar, showNotesSidebar, showNotificationBar, showPinned }
  = storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <NotificationSidebar v-model="showNotificationBar" />
  <PinnedSidebar v-model="showPinned" />
  <UserNotesSidebar v-model="showNotesSidebar" />
  <HelpSidebar
    v-model="showHelpBar"
    @about="showAbout = true"
  />
</template>
