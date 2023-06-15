<script setup lang="ts">
import { useListeners } from 'vue';
import IMask, { type InputMask } from 'imask';

const props = withDefaults(
  defineProps<{
    integer?: boolean;
    value?: string;
  }>(),
  {
    integer: false,
    value: ''
  }
);

const emit = defineEmits<{
  (e: 'input', value: string): void;
}>();

const attrs = useAttrs();
const slots = useSlots();
const listeners = useListeners();

const filteredListeners = (listeners: any) => ({
  ...listeners,
  input: () => {}
});

const { integer, value } = toRefs(props);
const { thousandSeparator, decimalSeparator } = storeToRefs(
  useFrontendSettingsStore()
);

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
    scale: get(integer) ? 0 : 100
  });

  const propValue = get(value);
  if (propValue) {
    newImask.unmaskedValue = propValue;
    set(currentValue, newImask.value);
  }

  set(imask, newImask);
});

watch(value, value => {
  const imaskVal = get(imask);
  if (imaskVal) {
    imaskVal.unmaskedValue = value;
    set(currentValue, imaskVal.value);
  }
});

watch(
  () => get(imask)?.unmaskedValue,
  unmasked => {
    const value = get(imask)?.value || '';
    set(currentValue, value);
    emit('input', unmasked || '');
  }
);

const focus = () => {
  const inputWrapper = get(textInput) as any;
  if (inputWrapper) {
    inputWrapper.focus();
  }
};

defineExpose({
  focus
});

const onFocus = () => {
  const inputWrapper = get(textInput)!;
  const input = inputWrapper.$el.querySelector('input') as HTMLInputElement;

  nextTick(() => {
    input.value = get(currentValue);
  });
};
</script>

<template>
  <v-text-field
    ref="textInput"
    :value="currentValue"
    v-bind="attrs"
    v-on="filteredListeners(listeners)"
    @focus="onFocus()"
  >
    <!-- Pass on all named slots -->
    <slot v-for="slot in Object.keys(slots)" :slot="slot" :name="slot" />

    <!-- Pass on all scoped slots -->
    <template v-for="slot in Object.keys($scopedSlots)" #[slot]="scope">
      <slot v-bind="scope" :name="slot" />
    </template>
  </v-text-field>
</template>
