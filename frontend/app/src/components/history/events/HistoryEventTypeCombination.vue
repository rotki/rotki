<script setup lang="ts">
import type { HistoryEventCategoryDetailWithId } from '@/types/history/events/event-type';
import type { RuiIcons } from '@rotki/ui-library';

const props = withDefaults(
  defineProps<{
    type: HistoryEventCategoryDetailWithId;
    showLabel?: boolean;
    icon?: RuiIcons;
    highlight?: boolean;
  }>(),
  {
    showLabel: false,
  },
);

const { type } = toRefs(props);

const directionIcon = computed<RuiIcons>(() => {
  switch (get(type).direction) {
    case 'in':
      return 'lu-arrow-down';
    case 'out':
      return 'lu-arrow-up';
    default:
      return 'lu-arrow-up-down';
  }
});

const { t } = useI18n();
</script>

<template>
  <div class="flex items-center gap-3">
    <div
      class="shrink-0 bg-rui-grey-200 dark:bg-rui-grey-900 text-rui-grey-600 dark:text-rui-grey-400 size-10 flex items-center justify-center rounded-full"
      :class="{
        '!bg-rui-primary-lighter/[0.7] dark:!bg-rui-primary-lighter !text-rui-primary': highlight,
      }"
    >
      <RuiIcon
        size="20"
        :name="icon || type.icon"
        :color="type.color"
      />
    </div>
    <div
      v-if="showLabel"
      class="flex items-center gap-2"
    >
      <div class="font-bold uppercase text-sm">
        {{ type.label }}
      </div>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <div class="cursor-pointer rounded-full bg-rui-grey-200 dark:bg-rui-grey-800 p-1">
            <RuiIcon
              size="14"
              :name="directionIcon"
            />
          </div>
        </template>
        <i18n-t
          tag="span"
          keypath="backend_mappings.events.type_direction.title"
          class="whitespace-break-spaces"
        >
          <template #direction>
            <span class="whitespace-nowrap font-bold">
              {{ t(`backend_mappings.events.type_direction.directions.${type.direction}`) }}
            </span>
          </template>
        </i18n-t>
      </RuiTooltip>
    </div>
  </div>
</template>
