<script setup lang="ts" generic="TTarget extends { kind: string }">
import type { ContextColorsType } from '@rotki/ui-library';
import { type ActionItem, ActionUrgency } from '@/modules/core/action-center/types';

const { color, item } = defineProps<{
  item: ActionItem<TTarget>;
  color?: ContextColorsType;
}>();

const emit = defineEmits<{
  action: [item: ActionItem<TTarget>];
  option: [target: TTarget];
}>();
</script>

<template>
  <RuiMenu
    v-if="item.choices.length > 0"
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        size="sm"
        :variant="item.urgency === ActionUrgency.AUTOMATIC ? 'text' : 'outlined'"
        :color="color"
        class="shrink-0"
        data-testid="actions-center-row-action"
        v-bind="attrs"
      >
        {{ item.actionLabel }}
        <template #append>
          <RuiIcon
            name="lu-chevron-down"
            size="14"
          />
        </template>
      </RuiButton>
    </template>
    <div class="py-2">
      <RuiButton
        v-for="choice in item.choices"
        :key="choice.id"
        variant="list"
        data-testid="actions-center-row-choice"
        :data-key="choice.id"
        @click="emit('option', choice.target)"
      >
        <template #prepend>
          <RuiIcon :name="choice.icon" />
        </template>
        {{ choice.label }}
      </RuiButton>
    </div>
  </RuiMenu>

  <RuiButton
    v-else
    size="sm"
    :variant="item.urgency === ActionUrgency.AUTOMATIC ? 'text' : 'outlined'"
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
</template>
