<script setup lang="ts">
import { useOperatorLabels } from '@/modules/core/table/pill/composables/use-operator-labels';
import { pillOperator, pillValueCaption, pillValueSummary } from '@/modules/core/table/pill/core/format';
import { resolveText } from '@/modules/core/table/pill/core/text';
import { type ActiveFilter, DisplayKinds, type FieldDef } from '@/modules/core/table/pill/core/types';
import PillValueIcon from '@/modules/core/table/pill/PillValueIcon.vue';
import EvmChainIcon from '@/modules/shell/components/EvmChainIcon.vue';

const { field, filter, disabled = false, removeLabel } = defineProps<{
  field: FieldDef;
  filter: ActiveFilter;
  disabled?: boolean;
  /**
   * Accessible name for the remove button, which is otherwise an icon with no text. Required
   * rather than defaulted: an empty default reads as a labelled button to the compiler and as an
   * unnamed one to a screen reader, which is the failure it exists to prevent.
   */
  removeLabel: string;
}>();

const emit = defineEmits<{
  edit: [];
  remove: [];
}>();

// Values past this many collapse into a "+N" count, keeping a pill a scannable fixed width.
const ICON_VALUE_CAP = 2;

const operatorLabels = useOperatorLabels();
const operator = computed<string | undefined>(() => {
  const op = pillOperator(field, filter);
  return op ? get(operatorLabels)[op] : undefined;
});
// Empty for a boolean field (on-once-added) or a not-yet-filled pill: no value segment then.
const summary = computed<string>(() => pillValueSummary(field, filter));
// Muted secondary text on a single-value pill (e.g. an account's address under its name).
const caption = computed<string>(() => pillValueCaption(field, filter));

const isAsset = computed<boolean>(() => field.display === DisplayKinds.ASSET);
const isAddress = computed<boolean>(() => field.display === DisplayKinds.ADDRESS);
// Icons come from the field's own resolvers, so a value looks the same on a pill as in its checklist.
const hasValueIcons = computed<boolean>(() =>
  Boolean(field.display) || Boolean(field.resolveDisplay) || Boolean(field.resolveIcon) || Boolean(field.resolveSwatch),
);
const iconValues = computed<string[]>(() => (get(hasValueIcons) ? filter.values.slice(0, ICON_VALUE_CAP) : []));
const extraValues = computed<number>(() => Math.max(0, filter.values.length - ICON_VALUE_CAP));

function chainOf(value: string): string | undefined {
  return get(isAsset) ? field.resolveChain?.(value) : undefined;
}

function valueLabel(value: string): string {
  return field.resolveLabel?.(value) ?? value;
}
</script>

<template>
  <div
    class="inline-flex items-stretch h-7 text-[13px] leading-none rounded-md overflow-hidden border border-rui-grey-300 dark:border-rui-grey-700 bg-white dark:bg-rui-grey-900 shadow-sm select-none"
    :class="disabled ? 'opacity-60' : 'cursor-pointer'"
    data-testid="filter-pill"
    :data-field="field.key"
    @click="!disabled && emit('edit')"
  >
    <!-- The height is pinned here rather than left to the contents: a pill carrying an icon or a
         caption came out taller than a bare text one, so a bar holding a mix looked ragged. Each
         segment centres within it instead of adding its own vertical padding.

         Everything but the remove control is one button, so the pill can be reached by Tab and
         reopened with Enter or Space. It cannot be the root element: the remove control is a
         button too, and a button inside a button is invalid. The click bubbles to the root, which
         carries the menu activator, so opening works the same by keyboard as by mouse. -->
    <button
      type="button"
      class="flex items-stretch text-left"
      :disabled="disabled"
      data-testid="filter-pill-open"
    >
      <span
        class="flex items-center gap-1.5 px-2 font-medium text-rui-text-secondary"
        :class="{ 'hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800': !disabled }"
      >
        {{ resolveText(field.label) }}
        <span
          v-if="operator"
          class="text-rui-primary font-semibold"
        >
          {{ operator }}
        </span>
      </span>

      <template v-if="summary || iconValues.length > 0">
        <span class="w-px bg-rui-grey-200 dark:bg-rui-grey-700" />
        <span
          class="flex items-center gap-1.5 px-2 font-semibold text-rui-text-primary"
          :class="{ 'hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800': !disabled }"
          data-testid="filter-pill-value"
        >
          <template v-if="iconValues.length > 0">
            <span
              v-for="value in iconValues"
              :key="value"
              class="flex items-center gap-1"
              :class="{ 'font-mono': isAddress }"
            >
              <PillValueIcon
                :display="field.display"
                :value-display="field.resolveDisplay?.(value)"
                :icon="field.resolveIcon?.(value)"
                :swatch="field.resolveSwatch?.(value)"
                :value="value"
              />
              {{ valueLabel(value) }}
              <EvmChainIcon
                v-if="chainOf(value)"
                :chain="chainOf(value)!"
                size="14px"
                tooltip
              />
            </span>
            <span v-if="extraValues">+{{ extraValues }}</span>
            <span
              v-if="caption"
              class="font-mono font-normal text-rui-text-secondary"
            >
              {{ caption }}
            </span>
          </template>
          <template v-else>
            {{ summary }}
            <span
              v-if="caption"
              class="font-mono font-normal text-rui-text-secondary"
            >
              {{ caption }}
            </span>
          </template>
        </span>
      </template>
    </button>

    <button
      v-if="!disabled"
      type="button"
      class="flex items-center px-1.5 border-l border-rui-grey-200 dark:border-rui-grey-700 text-rui-text-secondary hover:text-rui-error hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800"
      data-testid="filter-pill-remove"
      :aria-label="removeLabel"
      :title="removeLabel"
      @click.stop="emit('remove')"
    >
      <RuiIcon
        name="lu-x"
        size="14"
        aria-hidden="true"
      />
    </button>
  </div>
</template>
