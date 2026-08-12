<script setup lang="ts">
import type { ContextColorsType } from '@rotki/ui-library';
import type { HistoryEventIssue, HistoryIssueSeverity } from '@/modules/history/events/actions-center/use-history-event-issues';
import { useLinks } from '@/modules/shell/layout/use-links';

const { issue } = defineProps<{
  issue: HistoryEventIssue;
}>();

const emit = defineEmits<{
  action: [issue: HistoryEventIssue];
}>();

const SEVERITY_COLORS: Record<HistoryIssueSeverity, ContextColorsType | undefined> = {
  info: 'info',
  muted: undefined,
  warning: 'warning',
};

const SEVERITY_ICON_CLASSES: Record<HistoryIssueSeverity, string> = {
  info: 'bg-rui-info/10 text-rui-info',
  muted: 'bg-rui-grey-200 dark:bg-rui-grey-800 text-rui-text-secondary',
  warning: 'bg-rui-warning/10 text-rui-warning',
};

const MUTED_ICON_CLASS = 'bg-rui-grey-200 dark:bg-rui-grey-800 text-rui-text-disabled';

const { t } = useI18n({ useScope: 'global' });
const { href, linkTarget, onLinkClick } = useLinks();

const color = computed<ContextColorsType | undefined>(() => issue.locked ? undefined : SEVERITY_COLORS[issue.severity]);

const iconClass = computed<string>(() => issue.locked ? MUTED_ICON_CLASS : SEVERITY_ICON_CLASSES[issue.severity]);

const lockedHint = computed<string>(() => issue.minimumTier
  ? t('transactions.alerts.locked_hint', { tier: issue.minimumTier })
  : t('transactions.alerts.locked_hint_generic'));
</script>

<template>
  <div
    class="flex items-center gap-3 py-3"
    :class="{ 'opacity-60': issue.locked }"
    data-testid="actions-center-row"
    :data-key="issue.id"
  >
    <div
      class="shrink-0 rounded-full p-2"
      :class="iconClass"
    >
      <RuiIcon
        :name="issue.icon"
        size="18"
      />
    </div>

    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 flex-wrap">
        <span
          class="font-medium"
          :class="issue.locked ? 'text-rui-text-secondary' : 'text-rui-text'"
        >
          {{ issue.title }}
        </span>
        <RuiChip
          size="sm"
          :color="color"
          variant="outlined"
          class="!h-5 !px-1.5 tabular-nums"
          data-testid="actions-center-row-count"
        >
          {{ issue.count }}
        </RuiChip>
      </div>
      <p class="text-caption text-rui-text-secondary">
        {{ issue.locked ? lockedHint : issue.description }}
      </p>
    </div>

    <RuiTooltip
      v-if="issue.locked"
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          size="sm"
          variant="text"
          :href="href"
          :tag="href ? 'a' : 'button'"
          :target="linkTarget"
          class="shrink-0 !text-rui-text-secondary"
          data-testid="actions-center-row-locked"
          @click="onLinkClick()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-lock-keyhole"
              size="14"
            />
          </template>
          {{ t('transactions.alerts.locked') }}
        </RuiButton>
      </template>
      {{ lockedHint }}
    </RuiTooltip>

    <RuiButton
      v-else
      size="sm"
      :variant="issue.severity === 'muted' ? 'text' : 'outlined'"
      :color="color"
      class="shrink-0"
      data-testid="actions-center-row-action"
      @click="emit('action', issue)"
    >
      {{ issue.actionLabel }}
      <template #append>
        <RuiIcon
          name="lu-chevron-right"
          size="14"
        />
      </template>
    </RuiButton>
  </div>
</template>
