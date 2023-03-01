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
    <notification-sidebar
      :visible="showNotificationBar"
      @close="showNotificationBar = false"
    />
    <help-sidebar
      :visible="showHelpBar"
      @visible:update="showHelpBar = $event"
      @about="showAbout = true"
    />
    <pinned-sidebar
      :visible="showPinned"
      @visible:update="showPinned = $event"
    />
    <user-notes-sidebar
      :visible="showNotesSidebar"
      @visible:update="showNotesSidebar = $event"
    />
  </div>
</template>
