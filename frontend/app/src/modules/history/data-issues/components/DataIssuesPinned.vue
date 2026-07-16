<script setup lang="ts">
import DataIssuesPanelContent from '@/modules/history/data-issues/components/DataIssuesPanelContent.vue';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const { unpin } = usePinnedPanel(PinnedNames.DATA_ISSUES);
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <DataIssuesPanelContent
      @close="unpin()"
    />
  </div>
</template>
