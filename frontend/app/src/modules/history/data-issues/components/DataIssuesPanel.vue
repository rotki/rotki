<script setup lang="ts">
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import DataIssuesPanelContent from '@/modules/history/data-issues/components/DataIssuesPanelContent.vue';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { PinnedNames } from '@/modules/session/types';

const { pinned } = storeToRefs(useAreaVisibilityStore());
const { overlayVisible } = storeToRefs(useDataIssuesInboxStore());

const subDialogOpen = ref<boolean>(false);

/** Hand the panel off to the shared pinned rail so it slides in (and can be resized) like the other pinned panels. */
function pin(): void {
  set(pinned, { name: PinnedNames.DATA_ISSUES, props: {} });
  set(overlayVisible, false);
}

// This overlay only exists within the history view; close it when the view unmounts so
// it does not reappear elsewhere. A panel handed off to the pinned rail is unaffected.
onUnmounted(() => {
  set(overlayVisible, false);
});
</script>

<template>
  <RuiNavigationDrawer
    v-model="overlayVisible"
    width="400px"
    position="right"
    temporary
    :stateless="subDialogOpen"
  >
    <DataIssuesPanelContent
      v-model:sub-dialog-open="subDialogOpen"
      :pinned="false"
      @close="overlayVisible = false"
      @toggle-pin="pin()"
    />
  </RuiNavigationDrawer>
</template>
