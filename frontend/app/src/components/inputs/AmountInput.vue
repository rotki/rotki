<script setup lang="ts">
import IMask, { type InputMask } from 'imask';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string>({ required: true });

const props = withDefaults(
  defineProps<{
    integer?: boolean;
    hideDetails?: boolean;
  }>(),
  {
    hideDetails: false,
    integer: false,
  },
);

const { integer } = toRefs(props);
const { decimalSeparator, thousandSeparator } = storeToRefs(useFrontendSettingsStore());

const textInput = ref<any>(null);
const imask = ref<InputMask<any> | null>(null);
const currentValue = ref<string>('');

function removeLeadingZeros(
  value?: string,
  decimalSep: string = '.',
): string {
  if (!value)
    return '';

  // Special case: single "0" should stay as "0"
  if (value === '0')
    return value;

  // Split the number into parts before and after decimal separator
  const parts = value.split(decimalSep);

  if (parts.length === 0)
    return value;

  if (parts.length === 1) {
    // Check if there are leading zeros
    if (!/^0+/.test(parts[0])) {
      // No leading zeros, return the original value
      return parts[0];
    }

    // Has leading zeros - only remove the leading zeros
    return parts[0].replace(/^0+/, '') || '0'; // Return '0' if all zeros
  }

  // For numbers with decimal parts
  if (!/^0+/.test(parts[0])) {
    // No leading zeros before decimal, return original format
    return value;
  }

  // Has leading zeros before decimal - only remove the leading zeros
  return (parts[0].replace(/^0+/, '') || '0') + decimalSep + parts[1];
}

onMounted(() => {
  const inputWrapper = get(textInput)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  const decimal = get(decimalSeparator);
  const thousand = get(thousandSeparator);

  const newImask = IMask(input, {
    mask: Number,
    radix: decimal,
    scale: get(integer) ? 0 : 100,
    thousandsSeparator: thousand,
  });

  newImask.on('accept', () => {
    const mask = get(imask);
    if (mask) {
      set(model, mask?.unmaskedValue || '');
      setCurrentValue(mask.value);
    }
  });

  const propValue = get(model);
  if (propValue) {
    newImask.unmaskedValue = propValue;
    setCurrentValue(newImask.value);
  }

  set(imask, newImask);
});

function setCurrentValue(value?: string) {
  const formattedValue = removeLeadingZeros(value, get(decimalSeparator));
  set(currentValue, formattedValue);
  const imaskVal = get(imask);
  if (formattedValue !== value && imaskVal) {
    imaskVal.value = formattedValue;
    get(imask)?.updateValue();
  }
}

watch(model, (value) => {
  const imaskVal = get(imask);
  if (imaskVal) {
    imaskVal.unmaskedValue = value;
    setCurrentValue(imaskVal.value);
  }
});

function focus() {
  const inputWrapper = get(textInput) as any;
  if (inputWrapper)
    inputWrapper.focus();
}

function onFocus() {
  const inputWrapper = get(textInput)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  nextTick(() => {
    input.value = get(currentValue);
  });
}

function update(value: string) {
  if (!value) {
    set(model, '');
  }
}

defineExpose({
  focus,
});
</script>

<template>
  <RuiTextField
    ref="textInput"
    color="primary"
    :model-value="currentValue"
    v-bind="$attrs"
    :hide-details="hideDetails"
    @focus="onFocus()"
    @update:model-value="update($event)"
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
