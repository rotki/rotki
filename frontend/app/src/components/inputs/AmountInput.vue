<script setup lang="ts">
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { logger } from '@/utils/logging';
import { assert } from '@rotki/common';
import { RuiTextField } from '@rotki/ui-library';
import IMask, { type InputMask } from 'imask';

interface AmountInputProps {
  integer?: boolean;
  hideDetails?: boolean;
  rawInput?: boolean;
}

interface MaskConfig {
  mask: NumberConstructor;
  radix: string;
  scale: number;
  thousandsSeparator: string;
}

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<string>({ required: true });

const props = withDefaults(defineProps<AmountInputProps>(), {
  hideDetails: false,
  integer: false,
  rawInput: false,
});

const { integer, rawInput } = toRefs(props);
const { decimalSeparator, thousandSeparator } = storeToRefs(useFrontendSettingsStore());

const textInput = useTemplateRef<InstanceType<typeof RuiTextField>>('textInput');
const rawTextInput = useTemplateRef<InstanceType<typeof HTMLInputElement>>('rawTextInput');
const maskInstance = ref<InputMask<MaskConfig>>();
const currentValue = ref<string>('');

const EMPTY_VALUE = '';
const SINGLE_ZERO = '0';

const internalModelValue = computed({
  get() {
    return get(currentValue);
  },
  set(value?: string) {
    if (value) {
      return;
    }
    set(modelValue, '');
  },
});

function removeLeadingZeros(value?: string, decimalsSeparator: string = '.'): string {
  if (!value)
    return EMPTY_VALUE;

  if (value === SINGLE_ZERO)
    return value;

  const [integerPart, decimalPart] = value.split(decimalsSeparator);

  if (integerPart === undefined || integerPart === SINGLE_ZERO)
    return value;

  const hasLeadingZeros = /^0+/.test(integerPart);
  if (!hasLeadingZeros) {
    return value;
  }

  const cleanIntegerPart = integerPart.replace(/^0+/, '') || SINGLE_ZERO;
  return decimalPart ? `${cleanIntegerPart}${decimalsSeparator}${decimalPart}` : cleanIntegerPart;
}

function updateCurrentValue(mask: InputMask<any>) {
  const formattedValue = removeLeadingZeros(mask.value, get(decimalSeparator));
  set(currentValue, formattedValue);
  if (formattedValue !== mask.value) {
    nextTick(() => {
      mask.value = formattedValue;
      mask.updateValue();
    });
  }
}

function getInput(): HTMLInputElement {
  if (get(rawInput)) {
    const textField = get(rawTextInput);
    assert(textField, 'Input field is not defined');
    return textField;
  }
  const textField = get(textInput);
  assert(textField, 'Input field is not defined');
  return textField.$el.querySelector('input');
}

function focus() {
  getInput().focus();
}

function onFocus() {
  nextTick(() => {
    const input = getInput();
    input.value = get(currentValue);
  });
}

function initializeInputMask(input: HTMLInputElement) {
  const maskConfig: MaskConfig = {
    mask: Number,
    radix: get(decimalSeparator),
    scale: get(integer) ? 0 : 100,
    thousandsSeparator: get(thousandSeparator),
  };

  const newMask = IMask(input, maskConfig);

  newMask.on('accept', () => {
    const mask = get(maskInstance);
    if (mask) {
      set(modelValue, mask?.unmaskedValue || '');
      updateCurrentValue(mask);
    }
  });

  const propValue = get(modelValue);
  if (propValue) {
    newMask.unmaskedValue = propValue;
    updateCurrentValue(newMask);
  }

  set(maskInstance, newMask);
}

watch(modelValue, (value) => {
  if (isNaN(parseFloat(value)) && value !== '') {
    logger.warn('modelValue is not a number', value);
    return;
  }

  const mask = get(maskInstance);
  if (mask) {
    mask.unmaskedValue = value;
    updateCurrentValue(mask);
  }
});

onMounted(() => {
  initializeInputMask(getInput());
});

onBeforeUnmount(() => {
  get(maskInstance)?.destroy();
  set(maskInstance, undefined);
});

defineExpose({
  focus,
});
</script>

<template>
  <input
    v-if="rawInput"
    ref="rawTextInput"
    v-model="internalModelValue"
    v-bind="$attrs"
    @focus="onFocus()"
  />
  <RuiTextField
    v-else
    ref="textInput"
    v-model="internalModelValue"
    color="primary"
    v-bind="$attrs"
    :hide-details="hideDetails"
    @focus="onFocus()"
  >
    <template
      v-for="(_, name) in $slots"
      #[name]="scope"
    >
      <slot
        v-bind="scope"
        :name="name"
      />
    </template>
  </RuiTextField>
</template>
