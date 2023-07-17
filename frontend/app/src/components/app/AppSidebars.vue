<script setup lang="ts">
const {
  showAbout,
  showNotificationBar,
  showNotesSidebar,
  showHelpBar,
  showPinned
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
      @visible:update="showHelpBar = $event"
      @about="showAbout = true"
    />
    <PinnedSidebar
      :visible="showPinned"
      @visible:update="showPinned = $event"
    />
    <UserNotesSidebar
      :visible="showNotesSidebar"
      @visible:update="showNotesSidebar = $event"
    />
  </div>
</template>
