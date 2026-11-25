<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { RemediationTimelineItem } from '@/modules/history/data-issues/types';
import type { RemediationRequest } from '@/modules/history/data-issues/use-data-issue-remediation-actions';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import { RuiNavigationDrawer } from '@rotki/ui-library';
import { ref } from 'vue';
import DataIssueDecodingReview from '@/modules/history/data-issues/components/DataIssueDecodingReview.vue';
import DataIssueDetailContent from '@/modules/history/data-issues/components/DataIssueDetailContent.vue';

/**
 * Whether the drawer is showing.
 *
 * @remarks
 * This container is for the full data-issues page. The pinned rail uses a bottom sheet instead,
 * because a drawer opening beside the rail reads as a second, competing surface.
 */
const open = defineModel<boolean>({ required: true });

const { busy = false, failure, issue, modalOpen = false } = defineProps<{
  issue?: DataIssue;
  busy?: boolean;
  /** Keeps the drawer stateless while a child remediation dialog is open above it. */
  modalOpen?: boolean;
  /** The last failed dismiss or retry on this issue, named in its detail. */
  failure?: NamedFailure;
}>();

const emit = defineEmits<{
  dismiss: [id: number];
  remediate: [request: RemediationRequest];
  reopen: [id: number];
  retry: [id: number];
  resolve: [id: number];
}>();
const review = ref<RemediationTimelineItem>();
</script>

<template>
  <RuiNavigationDrawer
    v-model="open"
    below-app-bar
    width="570px"
    temporary
    :stateless="!!review || modalOpen"
    position="right"
    class="flex flex-col"
    :class-names="{ content: 'flex flex-col' }"
    data-testid="data-issue-detail-drawer"
  >
    <DataIssueDetailContent
      :issue="issue"
      :busy="busy"
      :failure="failure"
      @close="open = false"
      @dismiss="emit('dismiss', $event)"
      @remediate="emit('remediate', $event)"
      @reopen="emit('reopen', $event)"
      @retry="emit('retry', $event)"
      @resolve="emit('resolve', $event)"
      @review="review = $event"
    />
  </RuiNavigationDrawer>
  <DataIssueDecodingReview
    v-model="review"
    :asset="issue?.asset"
    @navigate="open = false"
  />
</template>
