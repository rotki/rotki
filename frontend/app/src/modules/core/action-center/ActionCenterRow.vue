<script setup lang="ts" generic="TTarget extends { kind: string }">
import type { ContextColorsType } from '@rotki/ui-library';
import ActionCenterRowAction from '@/modules/core/action-center/ActionCenterRowAction.vue';
import { type ActionItem, ActionUrgency } from '@/modules/core/action-center/types';
import { useLinks } from '@/modules/shell/layout/use-links';

const { isNew = false, item } = defineProps<{
  item: ActionItem<TTarget>;
  /** appeared, or grew, since the user last looked */
  isNew?: boolean;
}>();

const emit = defineEmits<{
  action: [item: ActionItem<TTarget>];
  option: [target: TTarget];
}>();

const URGENCY_COLORS: Record<ActionUrgency, ContextColorsType | undefined> = {
  [ActionUrgency.AUTOMATIC]: undefined,
  [ActionUrgency.DECISION]: 'warning',
  [ActionUrgency.TODO]: 'info',
};

const URGENCY_ICON_CLASSES: Record<ActionUrgency, string> = {
  [ActionUrgency.AUTOMATIC]: 'bg-rui-grey-200 dark:bg-rui-grey-800 text-rui-text-secondary',
  [ActionUrgency.DECISION]: 'bg-rui-warning/10 text-rui-warning',
  [ActionUrgency.TODO]: 'bg-rui-info/10 text-rui-info',
};

const LOCKED_ICON_CLASS = 'bg-rui-grey-200 dark:bg-rui-grey-800 text-rui-text-disabled';

const SET_ASIDE_ICON_CLASS = 'bg-rui-grey-200 dark:bg-rui-grey-800 text-rui-text-secondary';

const { t } = useI18n({ useScope: 'global' });
const { href, linkTarget, onLinkClick } = useLinks();

/** A row the user set aside (snoozed or dismissed) keeps its actions but drops its urgency colour. */
const toned = computed<boolean>(() => item.locked || item.informational);

const color = computed<ContextColorsType | undefined>(() => get(toned) ? undefined : URGENCY_COLORS[item.urgency]);

const iconClass = computed<string>(() => {
  if (item.locked)
    return LOCKED_ICON_CLASS;
  return item.informational ? SET_ASIDE_ICON_CLASS : URGENCY_ICON_CLASSES[item.urgency];
});

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
          :class="toned ? 'text-rui-text-secondary' : 'text-rui-text'"
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
        <span
          v-if="isNew"
          class="text-caption font-medium text-rui-primary"
          data-testid="actions-center-row-new"
        >
          {{ t('action_center.new') }}
        </span>
      </div>
      <p class="text-caption text-rui-text-secondary">
        {{ item.locked ? lockedHint : item.description }}
      </p>
      <div
        v-if="!item.locked && item.options.length > 0"
        class="flex flex-wrap gap-x-3 -ml-1.5"
      >
        <RuiButton
          v-for="option in item.options"
          :key="option.id"
          size="sm"
          variant="text"
          :color="option.danger ? 'error' : undefined"
          class="!px-1.5 !py-0.5 !text-caption"
          :class="{ '!text-rui-text-secondary': !option.danger }"
          data-testid="actions-center-row-option"
          :data-key="option.id"
          @click="emit('option', option.target)"
        >
          <template #prepend>
            <RuiIcon
              :name="option.icon"
              size="14"
            />
          </template>
          {{ option.label }}
        </RuiButton>
      </div>
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

    <ActionCenterRowAction
      v-else
      :item="item"
      :color="color"
      @action="emit('action', $event)"
      @option="emit('option', $event)"
    />
  </div>
</template>
