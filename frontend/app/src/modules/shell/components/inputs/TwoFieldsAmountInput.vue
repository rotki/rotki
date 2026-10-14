<script lang="ts" setup>
import { arrayify } from '@/modules/core/common/data/array';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

defineOptions({
  inheritAttrs: false,
});

const primaryValue = defineModel<string>('primaryValue', { required: true });
const secondaryValue = defineModel<string>('secondaryValue', { required: true });
const reversed = defineModel<boolean>('reversed', { default: false });

const {
  disabled = false,
  errorMessages = {},
  label = {},
  loading = false,
} = defineProps<{
  label?: { primary?: string; secondary?: string };
  errorMessages?: {
    primary?: string | string[];
    secondary?: string | string[];
  };
  loading?: boolean;
  disabled?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const input = useTemplateRef<InstanceType<typeof AmountInput>>('input');

const entered = computed<string>({
  get: () => (get(reversed) ? get(secondaryValue) : get(primaryValue)),
  set: (value: string) => {
    if (get(reversed))
      set(secondaryValue, value);
    else
      set(primaryValue, value);
  },
});

const derived = computed<string>(() => (get(reversed) ? get(primaryValue) : get(secondaryValue)));

const derivedLabel = computed<string | undefined>(() => (get(reversed) ? label.primary : label.secondary));

const enteredLabel = computed<string | undefined>(() => (get(reversed) ? label.secondary : label.primary));

const aggregatedErrorMessages = computed<string[]>(() => {
  const primary = errorMessages?.primary || [];
  const secondary = errorMessages?.secondary || [];

  return [...arrayify(primary), ...arrayify(secondary)];
});

type EnteredFigure = 'price' | 'value';

/**
 * The toggle's own values are strings: a bare `model-value` attribute on a button reaches its
 * generic prop as an empty string rather than `true`, which left the Value button doing nothing.
 */
const enteredFigure = computed<EnteredFigure>(() => (get(reversed) ? 'value' : 'price'));

/**
 * Switches between entering the price and entering the value, then focuses the field.
 *
 * @param figure - which figure is entered; a required group only ever emits a single value
 */
function choose(figure: EnteredFigure | EnteredFigure[] | undefined): void {
  if (figure !== 'price' && figure !== 'value')
    return;
  set(reversed, figure === 'value');
  nextTick(() => get(input)?.focus());
}
</script>

<template>
  <div v-bind="$attrs">
    <div class="mb-1 text-sm font-medium text-rui-text">
      {{ enteredLabel }}
    </div>
    <div class="flex items-start gap-2">
      <AmountInput
        ref="input"
        v-model="entered"
        class="min-w-0 flex-1"
        :label="enteredLabel"
        label-placement="hidden"
        :disabled="disabled"
        :error-messages="aggregatedErrorMessages"
        :hint="derived ? `${derivedLabel}: ${derived}` : undefined"
        :data-testid="reversed ? 'secondary' : 'primary'"
      >
        <template
          v-if="loading"
          #append
        >
          <RuiProgress
            circular
            variant="indeterminate"
            size="16"
            thickness="2"
            color="primary"
          />
        </template>
      </AmountInput>
      <RuiButtonGroup
        :model-value="enteredFigure"
        variant="segmented"
        class="shrink-0"
        required
        :disabled="disabled"
        data-testid="grouped-amount-input-swap"
        @update:model-value="choose($event)"
      >
        <RuiButton model-value="price">
          {{ t('common.price') }}
        </RuiButton>
        <RuiButton model-value="value">
          {{ t('common.value') }}
        </RuiButton>
      </RuiButtonGroup>
    </div>
  </div>
</template>
