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
  /**
   * The picker's calendar is open, so the bar must hold this editor open regardless of clicks.
   *
   * The calendar is teleported to the body, which puts it outside the editor's popover in the DOM:
   * `RuiMenu` closes on any click outside its own element and only ever ignores its activator, so
   * picking a day or pressing an action read as clicking away and shut the whole editor.
   */
  persist: [value: boolean];
}>();

// One flag per bound: `between` renders two pickers and either calendar can be the open one.
const fromMenuOpen = ref<boolean>(false);
const toMenuOpen = ref<boolean>(false);

watch([fromMenuOpen, toMenuOpen], ([from, to]) => emit('persist', from || to));

/**
 * Escape closes the editor only once the calendar is already shut.
 *
 * The picker binds escape inside its calendar to close it and hand focus back to the field, so
 * emitting unconditionally meant one press collapsed both layers at once. Innermost first: the
 * calendar goes, then the pill's editor.
 *
 * Withholding the emit is not enough on its own: `RuiMenu` closes itself on escape without
 * consulting `persistent` (rotki/ui-library#567), so a key that reaches the popover takes the
 * editor with it whatever this decides. While a calendar is up the key therefore stops here, on
 * the editor's own root, which sits below that popover in the bubble path. Once that issue is
 * fixed the `persist` channel covers this and the `stopPropagation` can go.
 *
 * The flags are read mid-dispatch on purpose. The picker mirrors its calendar into `menu-open`
 * from a watcher, so during the event they still hold the state from before the press, which is
 * the question being asked: was a calendar open when escape landed?
 */
function onEscape(event: KeyboardEvent): void {
  if (get(fromMenuOpen) || get(toMenuOpen)) {
    event.stopPropagation();
    return;
  }

  emit('close');
}

const { t } = useI18n({ useScope: 'global' });
const operatorLabels = useOperatorLabels();

const operators = computed<readonly FilterOp[]>(() => operatorsFor(field));
const showFrom = computed<boolean>(() => filter.op !== FilterOps.BEFORE);
const showTo = computed<boolean>(() => filter.op !== FilterOps.AFTER);

// The bounds are stored as strings holding the unix-second timestamp the picker emits, so the
// value is already wire-ready (backend `fromTimestamp`/`toTimestamp` are unix seconds) and the
// collapsed date field needs no serializer.
const fromValue = computed<number | undefined>(() => toEpoch(filter.date?.from));
const toValue = computed<number | undefined>(() => toEpoch(filter.date?.to));

/**
 * The bounds each picker allows. Neither end may sit in the future — nothing has happened yet
 * after now, and a `from` past the backend's default `to` of now is answered with a 400 — and a
 * `between` may not be written back to front, which would return an empty table with no
 * explanation. The old bar refused both through `dateRangeValidator`; the pickers enforce them
 * here, where the user can see the days that are out of range greyed out.
 */
const fromMaxDate = computed<number | 'now'>(() => get(toValue) ?? 'now');
const toMinDate = computed<number | undefined>(() => get(fromValue));

function toEpoch(value: string | undefined): number | undefined {
  if (value === undefined || value === '')
    return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function setOperator(op: FilterOp | FilterOp[] | undefined): void {
  if (op !== undefined && !Array.isArray(op))
    emit('update', { ...filter, op });
}

function setBound(bound: 'from' | 'to', value: number | Date | undefined): void {
  const normalized = typeof value === 'number' ? String(value) : undefined;
  emit('update', { ...filter, date: { ...filter.date, [bound]: normalized } });
}
</script>

<template>
  <!-- Escape is handled here rather than on each picker: the handler has to sit above both of them
       and below the menu popover to be able to keep the key from reaching it. -->
  <div
    class="flex flex-col gap-3 p-3 min-w-[16rem]"
    @keydown.esc="onEscape($event)"
  >
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
        :data-testid="`op-${op}`"
      >
        {{ operatorLabels[op] }}
      </RuiButton>
    </RuiButtonGroup>

    <!-- No `Now` action: the picker offers one by default, but as a filter bound this instant is
         either empty (From: nothing happened after now) or the same as no bound at all (To). -->
    <RuiDateTimePicker
      v-if="showFrom"
      v-model:menu-open="fromMenuOpen"
      :model-value="fromValue"
      :max-date="fromMaxDate"
      autofocus
      :actions="[]"
      type="epoch"
      accuracy="second"
      allow-empty
      dense
      variant="outlined"
      hide-details
      :label="t('transactions.filter.date_from')"
      data-testid="date-from"
      @keydown.enter="emit('close')"
      @update:model-value="setBound('from', $event)"
    />
    <RuiDateTimePicker
      v-if="showTo"
      v-model:menu-open="toMenuOpen"
      :model-value="toValue"
      :min-date="toMinDate"
      max-date="now"
      :autofocus="!showFrom"
      :actions="[]"
      type="epoch"
      accuracy="second"
      allow-empty
      dense
      variant="outlined"
      hide-details
      :label="t('transactions.filter.date_to')"
      data-testid="date-to"
      @keydown.enter="emit('close')"
      @update:model-value="setBound('to', $event)"
    />
  </div>
</template>
