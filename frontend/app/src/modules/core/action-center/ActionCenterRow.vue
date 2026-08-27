<script setup lang="ts" generic="TTarget extends { kind: string }">
import type { ContextColorsType } from '@rotki/ui-library';
import { type ActionItem, ActionSeverity } from '@/modules/core/action-center/types';
import { useLinks } from '@/modules/shell/layout/use-links';

const { item } = defineProps<{
  item: ActionItem<TTarget>;
}>();

const emit = defineEmits<{
  action: [item: ActionItem<TTarget>];
}>();

const SEVERITY_COLORS: Record<ActionSeverity, ContextColorsType | undefined> = {
  [ActionSeverity.INFO]: 'info',
  [ActionSeverity.MUTED]: undefined,
  [ActionSeverity.WARNING]: 'warning',
};

const SEVERITY_ICON_CLASSES: Record<ActionSeverity, string> = {
  [ActionSeverity.INFO]: 'bg-rui-info/10 text-rui-info',
  [ActionSeverity.MUTED]: 'bg-rui-grey-200 dark:bg-rui-grey-800 text-rui-text-secondary',
  [ActionSeverity.WARNING]: 'bg-rui-warning/10 text-rui-warning',
};

const MUTED_ICON_CLASS = 'bg-rui-grey-200 dark:bg-rui-grey-800 text-rui-text-disabled';

const { t } = useI18n({ useScope: 'global' });
const { href, linkTarget, onLinkClick } = useLinks();

const color = computed<ContextColorsType | undefined>(() => item.locked ? undefined : SEVERITY_COLORS[item.severity]);

const iconClass = computed<string>(() => item.locked ? MUTED_ICON_CLASS : SEVERITY_ICON_CLASSES[item.severity]);

const lockedHint = computed<string>(() => item.minimumTier
  ? t('action_center.locked_hint', { tier: item.minimumTier })
  : t('action_center.locked_hint_generic'));
</script>

<template>
  <div
    class="flex items-center gap-3 py-3"
    :class="{ 'opacity-60': item.locked }"
    data-testid="actions-center-row"
    :data-key="item.id"
  >
    <div
      class="shrink-0 rounded-full p-2"
      :class="iconClass"
    >
      <RuiIcon
        :name="item.icon"
        size="18"
      />
    </div>

    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 flex-wrap">
        <span
          class="font-medium"
          :class="item.locked ? 'text-rui-text-secondary' : 'text-rui-text'"
        >
          {{ item.title }}
        </span>
        <RuiChip
          size="sm"
          :color="color"
          variant="outlined"
          class="!h-5 !px-1.5 tabular-nums"
          data-testid="actions-center-row-count"
        >
          {{ item.count }}
        </RuiChip>
      </div>
      <p class="text-caption text-rui-text-secondary">
        {{ item.locked ? lockedHint : item.description }}
      </p>
    </div>

    <RuiTooltip
      v-if="item.locked"
      :options="{ placement: 'top' }"
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
          {{ t('action_center.locked') }}
        </RuiButton>
      </template>
      {{ lockedHint }}
    </RuiTooltip>

    <RuiButton
      v-else
      size="sm"
      :variant="item.severity === ActionSeverity.MUTED ? 'text' : 'outlined'"
      :color="color"
      class="shrink-0"
      data-testid="actions-center-row-action"
      @click="emit('action', item)"
    >
      {{ item.actionLabel }}
      <template #append>
        <RuiIcon
          name="lu-chevron-right"
          size="14"
        />
      </template>
    </RuiButton>
  </div>
</template>
