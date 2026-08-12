<script setup lang="ts">
import type { ActiveFilter, FieldDef, FilterOp } from '@/modules/core/table/pill/core/types';
import { FilterOps } from '@/modules/core/table/filtering';
import { useOperatorLabels } from '@/modules/core/table/pill/composables/use-operator-labels';
import { operatorsFor } from '@/modules/core/table/pill/core/operators';

const { field, filter } = defineProps<{
  field: FieldDef;
  filter: ActiveFilter;
}>();

const emit = defineEmits<{
  update: [filter: ActiveFilter];
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const operatorLabels = useOperatorLabels();

// The `autofocus` attribute is ignored for an input inserted into an already-loaded document, so
// the first bound is focused explicitly once the popover exists: opening the editor should leave
// the caret ready to type, not require a click.
const firstField = useTemplateRef<{ focus?: () => void }>('firstField');

onMounted(async () => {
  await nextTick();
  get(firstField)?.focus?.();
});

const operators = computed<readonly FilterOp[]>(() => operatorsFor(field));
const showMin = computed<boolean>(() => filter.op !== FilterOps.LT);
const showMax = computed<boolean>(() => filter.op !== FilterOps.GT);

// Local inputs so typing stays responsive; the filter update is debounced (below) rather than
// pushed on every keystroke, so the table is not refetched mid-edit.
const minInput = ref<string>(filter.range?.min ?? '');
const maxInput = ref<string>(filter.range?.max ?? '');

watch(() => filter.range, (range) => {
  set(minInput, range?.min ?? '');
  set(maxInput, range?.max ?? '');
});

// A filled max below a filled min is rejected: the update is not pushed and the field shows an
// inline error until it is corrected, so the bar never filters on an impossible range.
const invalid = computed<boolean>(() => {
  const min = Number(get(minInput));
  const max = Number(get(maxInput));
  if (get(minInput) === '' || get(maxInput) === '' || Number.isNaN(min) || Number.isNaN(max))
    return false;
  return max < min;
});

// Both fields carry the error so the guard is visible whichever bound the user is editing.
const rangeError = computed<string[]>(() => (get(invalid) ? [t('transactions.filter.range_max_below_min')] : []));

// Enter commits straight away instead of waiting out the debounce, and closes the editor, so a
// range can be typed and applied without reaching for the mouse. An invalid range stays open with
// its error showing.
function commitAndClose(): void {
  if (get(invalid))
    return;
  emitRange();
  emit('close');
}

/** What is typed right now, which is not the same as what has been committed. */
function currentRange(): { min?: string; max?: string } {
  return {
    max: get(maxInput) === '' ? undefined : get(maxInput),
    min: get(minInput) === '' ? undefined : get(minInput),
  };
}

function emitRange(): void {
  emit('update', { ...filter, range: currentRange() });
}

watchDebounced([minInput, maxInput], () => {
  if (!get(invalid))
    emitRange();
}, { debounce: 400 });

/**
 * Closing the editor commits, it does not cancel: everywhere else in the bar a change applies as
 * it is made, so a range vanishing because the mouse moved away inside the debounce window would
 * be the odd one out. Anything typed and still pending is banked before the editor goes.
 */
onBeforeUnmount(() => {
  if (get(invalid))
    return;
  const pending = currentRange();
  if (pending.min !== filter.range?.min || pending.max !== filter.range?.max)
    emitRange();
});

// Keep only the bound(s) the new operator shows, so a stale value can never leak into the pill
// (a "greater than" pill must not still carry a max). Read from what is typed rather than what
// was committed, or switching operators before the debounce lands would discard it.
function retainedRange(op: FilterOp): { min?: string; max?: string } {
  const current = currentRange();
  const range: { min?: string; max?: string } = {};
  if (op !== FilterOps.LT && current.min !== undefined)
    range.min = current.min;
  if (op !== FilterOps.GT && current.max !== undefined)
    range.max = current.max;
  return range;
}

function setOperator(op: FilterOp | FilterOp[] | undefined): void {
  if (op === undefined || Array.isArray(op))
    return;
  // Operator changes apply immediately (not debounced).
  const range = retainedRange(op);
  set(minInput, range.min ?? '');
  set(maxInput, range.max ?? '');
  emit('update', { ...filter, op, range });
}
</script>

<template>
  <div class="flex flex-col gap-3 p-3 min-w-[16rem]">
    <!-- A little more space under the chips than between the fields, so the operator reads as
         choosing the shape of the filter rather than as another field in the list. -->
    <RuiButtonGroup
      v-if="operators.length > 1"
      class="mb-1"
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
        data-testid="pill-op"
        :data-key="op"
      >
        {{ operatorLabels[op] }}
      </RuiButton>
    </RuiButtonGroup>

    <RuiTextField
      v-if="showMin"
      ref="firstField"
      v-model="minInput"
      type="number"
      dense
      variant="outlined"
      :error-messages="rangeError"
      :hide-details="!invalid"
      :label="t('transactions.filter.range_min')"
      data-testid="range-min"
      @keydown.enter="commitAndClose()"
    />
    <RuiTextField
      v-if="showMax"
      :ref="showMin ? undefined : 'firstField'"
      v-model="maxInput"
      type="number"
      dense
      variant="outlined"
      :error-messages="rangeError"
      :hide-details="!invalid"
      :label="t('transactions.filter.range_max')"
      data-testid="range-max"
      @keydown.enter="commitAndClose()"
    />
  </div>
</template>
