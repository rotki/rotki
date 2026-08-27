<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import DataIssueDetailContent from '@/modules/history/data-issues/components/DataIssueDetailContent.vue';

// Right-hand drawer container for the issue detail, used by the full data-issues page. The pinned
// rail uses a bottom sheet instead (see DataIssuesPanelContent), because a drawer opening beside
// the rail reads as a second, competing surface.
const open = defineModel<boolean>({ required: true });

const { issue, busy = false } = defineProps<{
  issue?: DataIssue;
  busy?: boolean;
}>();

const emit = defineEmits<{
  dismiss: [id: number];
  retry: [id: number];
  resolve: [id: number];
}>();
</script>

<template>
  <RuiNavigationDrawer
    v-model="open"
    width="570px"
    temporary
    position="right"
    class="flex flex-col"
    :class-names="{ content: 'flex flex-col' }"
    data-testid="data-issue-detail-drawer"
  >
    <DataIssueDetailContent
      :issue="issue"
      :busy="busy"
      @close="open = false"
      @dismiss="emit('dismiss', $event)"
      @retry="emit('retry', $event)"
      @resolve="emit('resolve', $event)"
    />
  </RuiNavigationDrawer>
</template>
