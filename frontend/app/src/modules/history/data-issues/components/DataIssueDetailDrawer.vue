<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import DataIssueRemediationTimeline from '@/modules/history/data-issues/components/DataIssueRemediationTimeline.vue';
import DataIssueStateChip from '@/modules/history/data-issues/components/DataIssueStateChip.vue';
import { canDismiss, canResolveManually, canRetry, IssueKind } from '@/modules/history/data-issues/constants';
import { describeIssue, toTimelineItems } from '@/modules/history/data-issues/transforms';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import { Routes } from '@/router/routes';

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

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const description = computed(() => {
  const current = issue;
  if (!current)
    return undefined;
  return describeIssue(current, (key, params) => t(key, params ?? {}));
});

/**
 * Deep-link to the offending history event. For a negative-balance issue we reuse
 * the events view's `highlightedNegativeBalanceEvent` query param, which highlights
 * the event (in error colour) by its identifier alone — no group lookup needed.
 */
const relatedEventLink = computed<RouteLocationRaw | undefined>(() => {
  const eventIdentifier = get(description)?.eventIdentifier;
  if (eventIdentifier === undefined)
    return undefined;

  const path = Routes.HISTORY_EVENTS.toString();
  if (issue?.kind === IssueKind.NEGATIVE_BALANCE)
    return { path, query: { highlightedNegativeBalanceEvent: eventIdentifier.toString() } };

  return { path };
});

async function goToRelatedEvent(): Promise<void> {
  const link = get(relatedEventLink);
  if (!link)
    return;
  set(open, false);
  await router.push(link);
}

const timeline = computed(() => (issue ? toTimelineItems(issue) : []));

const resolutionNote = computed<string | undefined>(() => {
  const resolution = issue?.payload?.resolution;
  if (resolution && typeof resolution === 'object' && 'note' in resolution) {
    const note = resolution.note;
    return typeof note === 'string' ? note : undefined;
  }
  return undefined;
});
</script>

<template>
  <RuiNavigationDrawer
    v-model="open"
    width="540px"
    temporary
    position="right"
    class="flex flex-col"
    content-class="flex flex-col"
    data-testid="data-issue-detail-drawer"
  >
    <div
      v-if="issue"
      class="flex flex-col h-full"
    >
      <div class="flex items-start justify-between gap-2 p-4 border-b border-default">
        <div class="flex flex-col gap-2">
          <h5 class="text-h6">
            {{ t('data_issues.detail.title') }}
          </h5>
          <div class="flex items-center gap-2 flex-wrap">
            <DataIssueKindChip :kind="issue.kind" />
            <DataIssueStateChip :state="issue.state" />
          </div>
        </div>
        <RuiButton
          variant="text"
          icon
          size="sm"
          @click="open = false"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </div>

      <div class="flex flex-col gap-6 p-4 overflow-y-auto grow">
        <section>
          <div class="text-overline text-rui-text-secondary mb-1">
            {{ t('data_issues.detail.whats_wrong') }}
          </div>
          <p class="text-body-1">
            {{ description?.summary }}
          </p>
          <RuiButton
            v-if="description?.eventIdentifier !== undefined && relatedEventLink"
            variant="text"
            color="primary"
            size="sm"
            class="mt-1 !px-0"
            data-testid="data-issue-related-event"
            @click="goToRelatedEvent()"
          >
            <template #append>
              <RuiIcon
                name="lu-arrow-up-right"
                size="16"
              />
            </template>
            {{ t('data_issues.detail.related_event', { id: description.eventIdentifier }) }}
          </RuiButton>
        </section>

        <section class="grid grid-cols-2 gap-4">
          <div>
            <div class="text-overline text-rui-text-secondary mb-1">
              {{ t('common.account') }}
            </div>
            <LocationDisplay
              v-if="issue.locationLabel"
              :identifier="issue.locationLabel"
              :opens-details="false"
            />
            <span
              v-else
              class="text-body-2 text-rui-text-secondary"
            >
              -
            </span>
          </div>
          <div>
            <div class="text-overline text-rui-text-secondary mb-1">
              {{ t('common.location') }}
            </div>
            <LocationDisplay :identifier="issue.location" />
          </div>
          <div v-if="issue.asset">
            <div class="text-overline text-rui-text-secondary mb-1">
              {{ t('common.asset') }}
            </div>
            <AssetDetails :asset="issue.asset" />
          </div>
          <div v-if="issue.protocol">
            <div class="text-overline text-rui-text-secondary mb-1">
              {{ t('common.protocol') }}
            </div>
            <span class="text-body-2">{{ issue.protocol }}</span>
          </div>
          <div>
            <div class="text-overline text-rui-text-secondary mb-1">
              {{ t('data_issues.detail.detected') }}
            </div>
            <DateDisplay :timestamp="issue.createdAt" />
          </div>
        </section>

        <section>
          <div class="text-overline text-rui-text-secondary mb-2">
            {{ t('data_issues.detail.remediation_history') }}
          </div>
          <DataIssueRemediationTimeline :items="timeline" />
        </section>

        <section v-if="resolutionNote">
          <div class="text-overline text-rui-text-secondary mb-1">
            {{ t('data_issues.detail.resolution_note') }}
          </div>
          <p class="text-body-2">
            {{ resolutionNote }}
          </p>
        </section>
      </div>

      <div class="flex items-center justify-end gap-2 p-4 border-t border-default">
        <RuiButton
          variant="outlined"
          :disabled="busy || !canDismiss(issue.state)"
          data-testid="data-issue-detail-dismiss"
          @click="emit('dismiss', issue.id)"
        >
          {{ t('data_issues.action.dismiss.label') }}
        </RuiButton>
        <RuiButton
          variant="outlined"
          color="primary"
          :disabled="busy || !canRetry(issue.state)"
          data-testid="data-issue-detail-retry"
          @click="emit('retry', issue.id)"
        >
          {{ t('data_issues.action.retry.label') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="busy || !canResolveManually(issue.state)"
          data-testid="data-issue-detail-resolve"
          @click="emit('resolve', issue.id)"
        >
          {{ t('data_issues.action.resolve.label') }}
        </RuiButton>
      </div>
    </div>
  </RuiNavigationDrawer>
</template>
