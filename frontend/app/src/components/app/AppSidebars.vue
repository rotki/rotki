<script setup lang="ts">
import HelpSidebar from '@/components/help/HelpSidebar.vue';
import UserNotesSidebar from '@/components/notes/UserNotesSidebar.vue';
import PinnedSidebar from '@/components/PinnedSidebar.vue';
import NotificationSidebar from '@/components/status/notifications/NotificationSidebar.vue';
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
