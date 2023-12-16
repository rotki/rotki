<script setup lang="ts">
const { showAbout, showNotificationBar, showNotesSidebar, showHelpBar, showPinned }
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
