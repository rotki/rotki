<script setup lang="ts">
import { type HistoryEventTypeDetailWithId } from '@/types/history/events/event-type';

const props = withDefaults(
  defineProps<{
    type: HistoryEventTypeDetailWithId;
    showLabel?: boolean;
  }>(),
  {
    showLabel: false
  }
);

const { dark } = useTheme();

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
  <div class="flex items-center gap-4">
    <VAvatar
      class="text--darken-4"
      :color="dark ? 'white' : 'grey lighten-3'"
      :size="36"
    >
      <VIcon :size="20" :color="type.color || 'grey darken-2'">
        {{ type.icon }}
      </VIcon>
    </VAvatar>
    <div v-if="showLabel" class="flex gap-2">
      <div class="font-bold text-uppercase text-sm">
        {{ type.label }}
      </div>
      <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
        <template #activator>
          <RuiChip size="sm" class="[&>span]:px-0">
            <RuiIcon size="14" :name="directionIcon" />
          </RuiChip>
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
