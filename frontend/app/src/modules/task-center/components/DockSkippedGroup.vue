<script setup lang="ts">
import type { Activity } from '@/modules/task-center/core/types';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { type ActivitySubject, activitySubject } from '@/modules/task-center/activity-subject';
import DockTrackAction from '@/modules/task-center/components/DockTrackAction.vue';
import { needsAttention } from '@/modules/task-center/core/status';
import { useActivityLabel } from '@/modules/task-center/use-activity-label';

const { activities, reason } = defineProps<{
  /** The skipped leaves the group stands for, in the order they sorted. */
  activities: Activity[];
  reason: string | undefined;
}>();

const { t } = useI18n({ useScope: 'global' });

const { labelOf } = useActivityLabel();

type AccountSubject = ActivitySubject & { readonly address: string };

function isAccount(subject: ActivitySubject | undefined): subject is AccountSubject {
  return subject?.address !== undefined;
}

/** How many names the row spells out before it only counts the rest. */
const NAMED = 3;

const rest = computed<number>(() => Math.max(0, activities.length - NAMED));

/**
 * The accounts the leaves act on, when every one of them names an address. They are then shown the
 * way an account row shows its own, shortened and private-mode aware, instead of as raw text.
 */
const accounts = computed<AccountSubject[] | undefined>(() => {
  const found = activities.map(activity => activitySubject(activity)).filter(isAccount);
  return found.length === activities.length ? found : undefined;
});

/** The addresses to offer tracking on a chain: every leaf an account the user was left without. */
const untracked = computed<string[]>(() => {
  const found = get(accounts);
  return found && activities.every(needsAttention) ? found.map(account => account.address) : [];
});

const names = computed<string>(() => {
  const shown = activities.slice(0, NAMED).map(activity => labelOf(activity, true)).join(', ');
  return get(rest) > 0 ? t('task_dock.panel.skipped_names_more', { count: get(rest), names: shown }) : shown;
});
</script>

<template>
  <div
    class="flex items-start gap-2.5 py-1 px-1"
    data-testid="dock-skipped-group"
  >
    <RuiIcon
      name="lu-skip-forward"
      size="16"
      class="shrink-0 mt-0.5 text-rui-warning"
    />
    <!-- The subject icon's slot, empty, so the label lines up with the chain rows beside it. -->
    <div class="size-5 shrink-0 -ml-1" />
    <div class="flex flex-col flex-1 min-w-0 gap-0.5">
      <div class="text-sm leading-5 text-rui-text-secondary">
        {{ t('task_dock.panel.skipped_count', { count: activities.length }, activities.length) }}
      </div>
      <div
        v-if="reason"
        class="text-xs leading-4 text-rui-text-secondary break-words"
      >
        {{ reason }}
      </div>
      <div
        v-if="accounts"
        class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs leading-4 text-rui-text-secondary"
        data-testid="dock-skipped-accounts"
      >
        <HashLink
          v-for="account in accounts.slice(0, NAMED)"
          :key="account.address"
          class="min-w-0"
          :text="account.address"
          :location="account.chain"
          size="12"
          reveal-actions
          data-testid="dock-skipped-account"
        />
        <span
          v-if="rest > 0"
          class="tabular-nums"
        >
          {{ t('task_dock.panel.skipped_more', { count: rest }) }}
        </span>
      </div>
      <div
        v-else
        class="text-xs leading-4 text-rui-text-secondary truncate"
        :title="activities.map(activity => labelOf(activity, true)).join(', ')"
        data-testid="dock-skipped-names"
      >
        {{ names }}
      </div>
      <DockTrackAction
        v-if="untracked.length > 0"
        :addresses="untracked"
      />
    </div>
  </div>
</template>
