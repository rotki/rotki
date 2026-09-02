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

/** How long typing settles before a single-value field pushes it, so the table is not refetched per keystroke. */
const KEYSTROKE_COMMIT_DEBOUNCE_MS = 300;

const { t } = useI18n({ useScope: 'global' });
const operatorLabels = useOperatorLabels();
const { scrambleAddress } = useScramble();

/**
 * The entry field, focused explicitly once the editor mounts.
 *
 * @remarks
 * `autofocus` is ignored by browsers for an input added to an already-loaded document, so the
 * editor has to take the focus itself.
 */
const textField = useTemplateRef<{ focus?: () => void }>('textField');

onMounted(async () => {
  await nextTick();
  get(textField)?.focus?.();
});

/**
 * Renders one committed token the way the collapsed pill renders it.
 *
 * @remarks
 * The field's own resolver owns the form, so a chip in the editor and the same value on the pill
 * cannot disagree; for an address that is what scrambles and shortens it. A field that declares no
 * resolver shows the raw value.
 */
function chipLabel(value: string): string {
  return field.resolveLabel?.(value) ?? value;
}

const isAddress = computed<boolean>(() => field.display === DisplayKinds.ADDRESS);
const operators = computed<readonly FilterOp[]>(() => operatorsFor(field));
const showOperators = computed<boolean>(() => get(operators).length > 1);

const input = ref<string>(field.multiple ? '' : (filter.values[0] ?? ''));

const validAddressPreview = computed<boolean>(() => get(isAddress) && isValidEthAddress(get(input).trim()));

// A non-empty entry that fails the field's optional validator is flagged and never committed.
const invalid = computed<boolean>(() => {
  const token = get(input).trim();
  return token.length > 0 && field.validate !== undefined && !field.validate(token);
});

/**
 * Whether the entry repeats a token a multi-value field has already committed.
 *
 * @remarks
 * Single-value fields are exempt: their input *is* the committed value, so every keystroke would
 * read as a duplicate of itself.
 */
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

/**
 * Whether a validated field should confirm the entry as acceptable before enter is pressed.
 *
 * @remarks
 * A field with no validator has nothing to confirm, so it never shows the mark.
 */
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

/**
 * Commits the typed entry, in whichever way the field's arity calls for.
 *
 * @remarks
 * A multi-value field banks the token and stays open for the next one; a single-value field is
 * finished and closes, so neither needs the mouse. The single-value path emits here rather than
 * leaving it to the debounced watch below, which Enter can outrun: closing unmounts the editor
 * with the debounce still pending and silently drops what was typed. A rejected entry commits
 * nothing either way.
 */
function onEnter(): void {
  if (field.multiple) {
    addToken();
    return;
  }
  if (get(rejected))
    return;

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

watchDebounced(input, (value) => {
  if (field.multiple || get(rejected))
    return;
  const token = value.trim();
  emitValues(token ? [token] : []);
}, { debounce: KEYSTROKE_COMMIT_DEBOUNCE_MS });

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
