<script setup lang="ts">
import type { ActiveFilter, FieldDef, FilterOp } from '@/modules/core/table/pill/core/types';
import { useOperatorLabels } from '@/modules/core/table/pill/composables/use-operator-labels';
import { operatorsFor } from '@/modules/core/table/pill/core/operators';
import PillValueIcon from '@/modules/core/table/pill/PillValueIcon.vue';
import ValueSelectList, { type SelectOption } from '@/modules/core/table/pill/ValueSelectList.vue';

const { field, filter } = defineProps<{
  field: FieldDef;
  filter: ActiveFilter;
}>();

const emit = defineEmits<{
  update: [filter: ActiveFilter];
  /** Escape in the list: the editor is done, so the bar can close its popover. */
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const operatorLabels = useOperatorLabels();

const operators = computed<readonly FilterOp[]>(() => operatorsFor(field));
const showOperators = computed<boolean>(() => get(operators).length > 1);
// Every option carries what the field can resolve for it, not just its label: an account's label
// is a name, or a shortened and scrambled address, so without the caption two accounts sharing a
// name are indistinguishable and without the keywords a pasted full address matches nothing.
const enumOptions = computed<SelectOption[]>(
  () => (field.suggest?.() ?? []).map(value => ({
    caption: field.resolveCaption?.(value),
    keywords: field.resolveKeywords?.(value),
    label: field.resolveLabel?.(value) ?? value,
    value,
  })),
);

const selected = computed<string[]>({
  get() {
    return filter.values;
  },
  set(values: string[]) {
    emit('update', { ...filter, values });
  },
});

function setOperator(op: FilterOp | FilterOp[] | undefined): void {
  if (op !== undefined && !Array.isArray(op))
    emit('update', { ...filter, op });
}
</script>

<template>
  <div class="flex flex-col min-w-[16rem]">
    <div
      v-if="showOperators"
      class="p-3 pb-2"
    >
      <RuiButtonGroup
        :model-value="filter.op"
        color="primary"
        size="sm"
        required
        @update:model-value="setOperator($event)"
      >
        <RuiButton
          v-for="op in operators"
          :key="op"
          :model-value="op"
          :data-testid="`op-${op}`"
        >
          {{ operatorLabels[op] }}
        </RuiButton>
      </RuiButtonGroup>
    </div>

    <ValueSelectList
      v-model="selected"
      :options="enumOptions"
      :multiple="field.multiple"
      :search-placeholder="t('common.actions.search')"
      :empty-text="t('data_table.no_data')"
      @close="emit('close')"
    >
      <template
        v-if="field.display || field.resolveIcon"
        #icon="{ value }"
      >
        <PillValueIcon
          :display="field.display"
          :icon="field.resolveIcon?.(value)"
          :value="value"
          size="18px"
        />
      </template>
    </ValueSelectList>
  </div>
</template>
