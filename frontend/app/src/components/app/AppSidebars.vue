<script setup lang="ts">
const {
  showAbout,
  showNotificationBar,
  showNotesSidebar,
  showHelpBar,
  showPinned,
} = storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <div>
    <NotificationSidebar
      :visible="showNotificationBar"
      @close="showNotificationBar = false"
    />
    <HelpSidebar
      :visible="showHelpBar"
      @update:visible="showHelpBar = $event"
      @about="showAbout = true"
    />
    <PinnedSidebar
      :visible="showPinned"
      @update:visible="showPinned = $event"
    />
    <UserNotesSidebar
      :visible="showNotesSidebar"
      @update:visible="showNotesSidebar = $event"
    />
  </div>
</template>
