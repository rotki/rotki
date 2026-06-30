<script setup lang="ts">
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import DataIssuesPanelContent from '@/modules/history/data-issues/components/DataIssuesPanelContent.vue';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';

const { pinned } = storeToRefs(useAreaVisibilityStore());
const { overlayVisible } = storeToRefs(useDataIssuesInboxStore());

/** Hand the panel back to the floating overlay. */
function unpin(): void {
  set(pinned, null);
  set(overlayVisible, true);
}

/** Dismiss the panel entirely. */
function close(): void {
  set(pinned, null);
  set(overlayVisible, false);
}
</script>

<template>
  <RuiCard
    no-padding
    variant="flat"
    class="!rounded-none h-full flex flex-col overflow-hidden"
    content-class="h-full min-h-0"
  >
    <DataIssuesPanelContent
      :pinned="true"
      @close="close()"
      @toggle-pin="unpin()"
    />
  </RuiCard>
</template>
