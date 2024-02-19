<script setup lang="ts">
import IMask, { type InputMask } from 'imask';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    integer?: boolean;
    modelValue?: string;
    hideDetails?: boolean;
  }>(),
  {
    integer: false,
    modelValue: '',
    hideDetails: false,
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: string): void;
}>();

const { integer, modelValue } = toRefs(props);
const { thousandSeparator, decimalSeparator } = storeToRefs(useFrontendSettingsStore());

const textInput: Ref<any> = ref(null);
const imask: Ref<InputMask<any> | null> = ref(null);
const currentValue: Ref<string> = ref('');

onMounted(() => {
  const inputWrapper = get(textInput)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  const newImask = IMask(input, {
    mask: Number,
    thousandsSeparator: get(thousandSeparator),
    radix: get(decimalSeparator),
    scale: get(integer) ? 0 : 100,
  });

  newImask.on('accept', () => {
    const mask = get(imask);
    const value = mask?.value || '';
    set(currentValue, value);
    emit('update:model-value', mask?.unmaskedValue || '');
  });

  const propValue = get(modelValue);
  if (propValue) {
    newImask.unmaskedValue = propValue;
    set(currentValue, newImask.value);
  }

  set(imask, newImask);
});

watch(modelValue, (value) => {
  const imaskVal = get(imask);
  if (imaskVal) {
    imaskVal.unmaskedValue = value;
    set(currentValue, imaskVal.value);
  }
});

function focus() {
  const inputWrapper = get(textInput) as any;
  if (inputWrapper)
    inputWrapper.focus();
}

defineExpose({
  focus,
});

function onFocus() {
  const inputWrapper = get(textInput)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  nextTick(() => {
    input.value = get(currentValue);
  });
}
</script>

<template>
  <RuiTextField
    ref="textInput"
    color="primary"
    :model-value="currentValue"
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
