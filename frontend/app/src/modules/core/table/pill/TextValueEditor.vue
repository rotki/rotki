<script setup lang="ts">
import { isValidEthAddress } from '@rotki/common';
import { useOperatorLabels } from '@/modules/core/table/pill/composables/use-operator-labels';
import { operatorsFor } from '@/modules/core/table/pill/core/operators';
import { resolveOptionalText, resolveText } from '@/modules/core/table/pill/core/text';
import { type ActiveFilter, DisplayKinds, type FieldDef, type FilterOp } from '@/modules/core/table/pill/core/types';
import { useScramble } from '@/modules/settings/use-scramble';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';

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
const { scrambleAddress } = useScramble();

// Focused explicitly rather than through `autofocus`, which browsers ignore for an input added to
// an already-loaded document.
const textField = useTemplateRef<{ focus?: () => void }>('textField');

onMounted(async () => {
  await nextTick();
  get(textField)?.focus?.();
});

// A committed token reads exactly as it does on the pill: the field's resolver owns the form,
// which for an address means scrambled and shortened.
function chipLabel(value: string): string {
  return field.resolveLabel?.(value) ?? value;
}

const isAddress = computed<boolean>(() => field.display === DisplayKinds.ADDRESS);
const operators = computed<readonly FilterOp[]>(() => operatorsFor(field));
const showOperators = computed<boolean>(() => get(operators).length > 1);

// A single-value field (notes) two-way binds to its one value; a multi field (tx hashes,
// addresses) accumulates typed tokens as chips.
const input = ref<string>(field.multiple ? '' : (filter.values[0] ?? ''));

const validAddressPreview = computed<boolean>(() => get(isAddress) && isValidEthAddress(get(input).trim()));

// A non-empty entry that fails the field's optional validator is flagged and never committed.
const invalid = computed<boolean>(() => {
  const token = get(input).trim();
  return token.length > 0 && field.validate !== undefined && !field.validate(token);
});

// A value already among the committed tokens is a no-op rather than a silent one: say so instead
// of swallowing the enter press.
//
// Multi-value fields only. A single-value field's input IS its committed value, so once the
// debounce below has banked what was typed, the field would be flagged as a duplicate of itself:
// the notes filter said "Already added" about the text sitting in its own box, and refused to
// commit any edit of it.
const duplicate = computed<boolean>(() => {
  const token = get(input).trim();
  return field.multiple && token.length > 0 && filter.values.includes(token);
});

const rejected = computed<boolean>(() => get(invalid) || get(duplicate));

const errorMessages = computed<string[]>(() => {
  if (get(duplicate))
    return [t('transactions.filter.duplicate_value')];
  if (get(invalid))
    return [resolveOptionalText(field.invalidHint) ?? t('transactions.filter.invalid_value')];
  return [];
});

// A validated field confirms a good entry too, so it is clear the value will be accepted before
// enter is pressed. Fields with no validator have nothing to confirm.
const validEntry = computed<boolean>(() => {
  const token = get(input).trim();
  return token.length > 0 && field.validate !== undefined && !get(rejected);
});

function emitValues(values: string[]): void {
  emit('update', { ...filter, values });
}

function addToken(): void {
  const token = get(input).trim();
  if (!token || get(rejected))
    return;
  emitValues([...filter.values, token]);
  set(input, '');
}

// Enter commits: a multi field banks the token and stays open for the next one, a single-value
// field is done and closes, so neither needs the mouse.
function onEnter(): void {
  if (field.multiple) {
    addToken();
    return;
  }
  if (get(rejected))
    return;
  // A single-value field otherwise commits through the debounced watch below, and Enter can beat
  // it: closing unmounts the editor with the debounce still pending, silently dropping what was
  // typed. Banking the value here makes Enter commit in its own right.
  const token = get(input).trim();
  emitValues(token ? [token] : []);
  emit('close');
}

function removeToken(value: string): void {
  emitValues(filter.values.filter(item => item !== value));
}

function setOperator(op: FilterOp | FilterOp[] | undefined): void {
  if (op !== undefined && !Array.isArray(op))
    emit('update', { ...filter, op });
}

// Single-value fields push the typed value directly (debounced so the table is not refetched on
// every keystroke); multi fields only commit on Enter via addToken.
watchDebounced(input, (value) => {
  if (field.multiple || get(rejected))
    return;
  const token = value.trim();
  emitValues(token ? [token] : []);
}, { debounce: 300 });

/**
 * Closing commits rather than cancels, the same as enter does: a value typed and then dismissed
 * by clicking away would otherwise be lost to the pending debounce.
 */
onBeforeUnmount(() => {
  if (field.multiple || get(rejected))
    return;
  const token = get(input).trim();
  if (token !== (filter.values[0] ?? ''))
    emitValues(token ? [token] : []);
});
</script>

<template>
  <div class="flex flex-col gap-3 p-3 w-[20rem]">
    <RuiButtonGroup
      v-if="showOperators"
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

    <div
      v-if="field.multiple && filter.values.length > 0"
      class="flex flex-wrap gap-1"
    >
      <button
        v-for="value in filter.values"
        :key="value"
        type="button"
        class="inline-flex items-center gap-1 pl-1 pr-1.5 py-0.5 rounded-full bg-rui-primary/10 text-xs text-rui-primary hover:bg-rui-primary/20"
        data-testid="text-chip"
        :data-key="value"
        @click="removeToken(value)"
      >
        <EnsAvatar
          v-if="isAddress"
          :address="scrambleAddress(value)"
          avatar
          size="16px"
          class="shrink-0"
        />
        <span class="truncate max-w-[10rem] font-mono">{{ chipLabel(value) }}</span>
        <RuiIcon
          name="lu-x"
          size="12"
          class="shrink-0"
        />
      </button>
    </div>

    <RuiTextField
      ref="textField"
      v-model="input"
      dense
      variant="outlined"
      :error-messages="errorMessages"
      :hide-details="errorMessages.length === 0"
      :label="resolveText(field.label)"
      :placeholder="field.multiple ? t('common.actions.add') : undefined"
      data-testid="text-input"
      @keydown.enter="onEnter()"
    >
      <template
        v-if="validAddressPreview"
        #prepend
      >
        <EnsAvatar
          :address="input.trim()"
          avatar
          size="20px"
        />
      </template>
      <template
        v-if="validEntry"
        #append
      >
        <RuiIcon
          name="lu-check"
          size="16"
          class="text-rui-success"
          data-testid="text-valid"
        />
      </template>
    </RuiTextField>
  </div>
</template>
