<script setup lang="ts">
import { type HistoryEventCategoryDetailWithId } from '@/types/history/events/event-type';

const props = withDefaults(
  defineProps<{
    type: HistoryEventCategoryDetailWithId;
    showLabel?: boolean;
  }>(),
  {
    showLabel: false
  }
);

const { type } = toRefs(props);

const directionIcon = computed(
  () =>
    ({
      in: 'arrow-down-line',
      out: 'arrow-up-line',
      neutral: 'arrow-up-down-line'
    })[get(type).direction]
);

const { t } = useI18n();
</script>

<template>
  <div class="flex items-center gap-3">
    <div
      class="bg-rui-grey-200 text-rui-grey-600 dark:text-rui-grey-800 w-9 h-9 flex items-center justify-center rounded-full"
    >
      <RuiIcon size="20" :name="type.icon" :color="type.color" />
    </div>
    <div v-if="showLabel" class="flex items-center gap-2">
      <div class="font-bold text-uppercase text-sm">
        {{ type.label }}
      </div>
      <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
        <template #activator>
          <div
            class="cursor-pointer rounded-full bg-rui-grey-200 dark:bg-rui-grey-800 p-1"
          >
            <RuiIcon size="14" :name="directionIcon" />
          </div>
        </template>
        <i18n
          tag="span"
          path="backend_mappings.events.type_direction.title"
          class="whitespace-break-spaces"
        >
          <template #direction>
            <span class="whitespace-nowrap font-bold">
              {{
                t(
                  `backend_mappings.events.type_direction.directions.${type.direction}`
                )
              }}
            </span>
          </template>
        </i18n>
      </RuiTooltip>
    </div>
  </div>
</template>
