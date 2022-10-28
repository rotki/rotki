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

<script setup lang="ts">
import { useAreaVisibilityStore } from '@/store/session/visibility';

const HelpSidebar = defineAsyncComponent(
  () => import('@/components/help/HelpSidebar.vue')
);
const NotificationSidebar = defineAsyncComponent(
  () => import('@/components/status/notifications/NotificationSidebar.vue')
);
const PinnedSidebar = defineAsyncComponent(
  () => import('@/components/PinnedSidebar.vue')
);
const UserNotesSidebar = defineAsyncComponent(
  () => import('@/components/UserNotesSidebar.vue')
);

const {
  showAbout,
  showNotificationBar,
  showNotesSidebar,
  showHelpBar,
  showPinned
} = storeToRefs(useAreaVisibilityStore());
</script>
