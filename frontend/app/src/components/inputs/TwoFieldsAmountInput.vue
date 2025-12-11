<script lang="ts" setup>
import AmountInput from '@/components/inputs/AmountInput.vue';
import { arrayify } from '@/utils/array';

defineOptions({
  inheritAttrs: false,
});

const primaryValue = defineModel<string>('primaryValue', { required: true });
const secondaryValue = defineModel<string>('secondaryValue', { required: true });
const reversed = defineModel<boolean>('reversed', { default: false });

const props = withDefaults(
  defineProps<{
    label?: { primary?: string; secondary?: string };
    errorMessages?: {
      primary?: string | string[];
      secondary?: string | string[];
    };
    loading?: boolean;
    disabled?: boolean;
  }>(),
  {
    disabled: false,
    errorMessages: () => ({}),
    label: () => ({}),
    loading: false,
  },
);

const { disabled, errorMessages } = toRefs(props);

const primaryInput = ref<InstanceType<typeof AmountInput> | null>(null);
const secondaryInput = ref<InstanceType<typeof AmountInput> | null>(null);

function reverse(): void {
  const newReversed = !get(reversed);
  set(reversed, newReversed);

  nextTick(() => {
    if (!newReversed)
      get(primaryInput)?.focus();
    else get(secondaryInput)?.focus();
  });
}

const aggregatedErrorMessages = computed<string[]>(() => {
  const val = get(errorMessages);
  const primary = val?.primary || [];
  const secondary = val?.secondary || [];

  return [...arrayify(primary), ...arrayify(secondary)];
});

const hasError = computed<boolean>(() => get(aggregatedErrorMessages).length > 0);

const focused = ref<boolean>(false);

const uiClasses = {
  disabledInput: `
    [&_label]:!border-t-0
    [&_label]:border
    [&_label]:border-[#0000006b]
    [&_label]:rounded-b
    [&_label]:!rounded-t-none
    [&_label]:!bg-rui-grey-300/40
    dark:[&_label]:border-white/[0.42]
    dark:[&_label]:!bg-rui-grey-800/40
    [&_input]:!pt-6
    [&_input]:!pb-2
  `,
  enabledInput: `
    [&_label]:border
    [&_label]:rounded-t
    [&_label]:!rounded-b-none
    [&_label]:!bg-transparent
    [&_input]:!pt-6
    [&_input]:!pb-2
  `,
} as const;
</script>

<template>
  <div
    class="relative flex [&>*]:!-my-px"
    :class="{
      'flex-col-reverse': get(reversed),
      'flex-col': !get(reversed),
      '[&_label]:border-dotted [&_label]:!border-rui-grey-400 dark:[&_label]:!border-rui-grey-700': disabled,
      '[&_label]:!border-rui-primary [&_label]:!border-2': focused,
      '[&_label]:!border-rui-error [&_label]:!border-2': hasError,

    }"
    v-bind="$attrs"
  >
    <AmountInput
      ref="primaryInput"
      v-model="primaryValue"
      :disabled="reversed || disabled"
      :hide-details="!reversed"
      variant="filled"
      persistent-hint
      data-cy="primary"
      :class="reversed ? uiClasses.disabledInput : uiClasses.enabledInput"
      :label="label.primary"
      :error-messages="aggregatedErrorMessages"
      @focus="focused = true"
      @blur="focused = false"
    />

    <RuiProgress
      class="relative z-[1]"
      :class="{ 'opacity-0': !loading }"
      variant="indeterminate"
      thickness="4"
      color="primary"
    />

    <AmountInput
      ref="secondaryInput"
      v-model="secondaryValue"
      :disabled="!reversed || disabled"
      :hide-details="reversed"
      variant="filled"
      persistent-hint
      data-cy="secondary"
      :class="reversed ? uiClasses.enabledInput : uiClasses.disabledInput"
      :label="label.secondary"
      :error-messages="aggregatedErrorMessages"
      @focus="focused = true"
      @blur="focused = false"
    />

    <RuiButton
      icon
      class="absolute right-5 top-14 transform -translate-y-1/2 z-[1] !p-2"
      color="primary"
      data-cy="grouped-amount-input__swap-button"
      @click="reverse()"
    >
      <RuiIcon
        size="16"
        name="lu-arrow-up-down"
      />
    </RuiButton>
  </div>
</template>
