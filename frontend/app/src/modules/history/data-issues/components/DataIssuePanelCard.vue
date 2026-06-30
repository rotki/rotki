<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { IssueDescription } from '@/modules/history/data-issues/types';
import { toHumanReadable } from '@rotki/common';
import DataIssueCardActions from '@/modules/history/data-issues/components/DataIssueCardActions.vue';
import DataIssueDescription from '@/modules/history/data-issues/components/DataIssueDescription.vue';
import DataIssueDetectedTime from '@/modules/history/data-issues/components/DataIssueDetectedTime.vue';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import DataIssueStateChip from '@/modules/history/data-issues/components/DataIssueStateChip.vue';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

const { issue, eventRoute, active = false } = defineProps<{
  issue: DataIssue;
  description: IssueDescription;
  eventRoute?: RouteLocationRaw;
  active?: boolean;
}>();

const emit = defineEmits<{
  open: [];
  goto: [route: RouteLocationRaw];
  dismiss: [issue: DataIssue];
  retry: [issue: DataIssue];
  resolve: [issue: DataIssue];
}>();

// The description is clamped to two lines; only show the full-text tooltip when it
// actually overflows. Re-checked on resize and on content changes (the amounts and
// resolved asset symbol arrive asynchronously and can change the height).
const descriptionRef = useTemplateRef<HTMLElement>('descriptionRef');
const descriptionTruncated = ref<boolean>(false);

function checkTruncation(): void {
  const el = get(descriptionRef);
  set(descriptionTruncated, !!el && el.scrollHeight > el.clientHeight + 1);
}

onMounted(async () => {
  await nextTick();
  checkTruncation();
});

useResizeObserver(descriptionRef, checkTruncation);
useMutationObserver(descriptionRef, checkTruncation, { characterData: true, childList: true, subtree: true });
</script>

<template>
  <RuiCard
    class="cursor-pointer transition-colors"
    :class="active
      ? '!border-rui-primary ring-1 ring-rui-primary bg-rui-primary/5'
      : 'hover:bg-rui-grey-50 dark:hover:bg-rui-grey-900'"
    no-padding
    content-class="overflow-hidden"
    data-testid="data-issues-panel-item"
    :data-active="active"
    @click="emit('open')"
  >
    <div class="flex items-stretch">
      <div class="flex flex-col gap-2 p-3 grow min-w-0">
        <div class="flex items-center gap-2">
          <DataIssueKindChip :kind="issue.kind" />
          <DataIssueStateChip :state="issue.state" />
          <DataIssueDetectedTime
            class="ml-auto shrink-0 text-caption text-rui-text-secondary"
            :timestamp="issue.createdAt"
          />
        </div>

        <RuiTooltip
          :disabled="!descriptionTruncated"
          :open-delay="400"
        >
          <template #activator>
            <div
              ref="descriptionRef"
              class="text-body-2 text-rui-text-secondary line-clamp-3 leading-relaxed h-[3lh]"
            >
              <DataIssueDescription
                :description="description"
                tag="span"
              />
            </div>
          </template>
          <div class="max-w-xs">
            <DataIssueDescription
              :description="description"
              tag="span"
            />
          </div>
        </RuiTooltip>

        <div class="flex items-center gap-2 text-caption text-rui-text-secondary">
          <AssetIcon
            v-if="issue.asset"
            :identifier="issue.asset"
            size="22px"
            :show-chain="false"
            class="shrink-0"
          />
          <RuiTooltip
            class="shrink-0"
            :open-delay="300"
          >
            <template #activator>
              <LocationDisplay
                :identifier="issue.location"
                icon
                size="20px"
                :open-details="false"
              />
            </template>
            <span class="capitalize">{{ issue.location }}</span>
          </RuiTooltip>
          <RuiTooltip
            v-if="issue.protocol"
            class="shrink-0"
            :open-delay="300"
          >
            <template #activator>
              <CounterpartyDisplay
                :counterparty="issue.protocol"
                icon
                size="20px"
              />
            </template>
            <span>{{ toHumanReadable(issue.protocol) }}</span>
          </RuiTooltip>
          <div
            v-if="issue.locationLabel"
            class="min-w-0"
          >
            <HistoryEventAccount
              :location="issue.location"
              :location-label="issue.locationLabel"
              dense
              class="min-w-0"
            />
          </div>
          <DataIssueCardActions
            class="ml-auto shrink-0"
            :issue="issue"
            :event-route="eventRoute"
            @goto="emit('goto', $event)"
            @dismiss="emit('dismiss', $event)"
            @retry="emit('retry', $event)"
            @resolve="emit('resolve', $event)"
          />
        </div>
      </div>

      <div class="flex items-center pr-2 text-rui-text-secondary opacity-50">
        <RuiIcon
          name="lu-chevron-right"
          size="18"
        />
      </div>
    </div>
  </RuiCard>
</template>
