<script setup lang="ts" generic="TTarget extends { kind: string }">
import type { ContextColorsType } from '@rotki/ui-library';
import { type ActionItem, ActionUrgency, leavesCenter } from '@/modules/core/action-center/types';

const { color, item } = defineProps<{
  item: ActionItem<TTarget>;
  color?: ContextColorsType;
}>();

const emit = defineEmits<{
  action: [item: ActionItem<TTarget>];
  option: [target: TTarget];
}>();

/** Outlined while the row asks for something; plain text for what rotki retries or the user set aside. */
const variant = computed<'text' | 'outlined'>(() =>
  item.urgency === ActionUrgency.AUTOMATIC || item.informational ? 'text' : 'outlined');

/** The chevron promises a trip elsewhere, so an action that works in place goes without it. */
const leadsAway = computed<boolean>(() => leavesCenter(item.target));
</script>

<template>
  <RuiMenu
    v-if="item.choices.length > 0"
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        size="sm"
        :variant="variant"
        :color="color"
        class="shrink-0"
        :loading="item.loading"
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
    :variant="variant"
    :color="color"
    class="shrink-0"
    :loading="item.loading"
    data-testid="actions-center-row-action"
    @click="emit('action', item)"
  >
    {{ item.actionLabel }}
    <template
      v-if="leadsAway"
      #append
    >
      <RuiIcon
        name="lu-chevron-right"
        size="14"
        data-testid="actions-center-row-action-chevron"
      />
    </template>
  </RuiButton>
</template>
