<script setup lang="ts">
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import NotificationSidebar from '@/modules/core/notifications/NotificationSidebar.vue';
import UserNotesSidebar from '@/modules/notes/UserNotesSidebar.vue';
import HelpSidebar from '@/modules/shell/components/HelpSidebar.vue';
import PinnedSidebar from '@/modules/shell/components/navigation/PinnedSidebar.vue';

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
