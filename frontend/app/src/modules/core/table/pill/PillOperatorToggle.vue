<script setup lang="ts">
import type { FieldDef, FilterOp } from '@/modules/core/table/pill/core/types';
import { useOperatorLabels } from '@/modules/core/table/pill/composables/use-operator-labels';
import { hasOperatorChoice, operatorsFor } from '@/modules/core/table/pill/core/operators';

/** The operator picker of a pill value editor. Renders nothing for a field with a single operator. */
const { field, op } = defineProps<{
  field: FieldDef;
  op: FilterOp;
}>();

const emit = defineEmits<{
  'update:op': [op: FilterOp];
}>();

const operatorLabels = useOperatorLabels();

const operators = computed<readonly FilterOp[]>(() => operatorsFor(field));

/** `RuiButtonGroup` types its value for multi-select too; a required single group only sends one. */
function select(value: FilterOp | FilterOp[] | undefined): void {
  if (value !== undefined && !Array.isArray(value))
    emit('update:op', value);
}
</script>

<template>
  <RuiButtonGroup
    v-if="hasOperatorChoice(field)"
    :model-value="op"
    color="primary"
    size="sm"
    required
    @update:model-value="select($event)"
  >
    <RuiButton
      v-for="item in operators"
      :key="item"
      :model-value="item"
      data-testid="pill-op"
      :data-key="item"
    >
      {{ operatorLabels[item] }}
    </RuiButton>
  </RuiButtonGroup>
</template>
