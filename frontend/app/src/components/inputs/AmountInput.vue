<template>
  <v-text-field
    ref="textInput"
    v-model="currentValue"
    v-bind="attrs"
    v-on="filteredListeners(listeners)"
  >
    <!-- Pass on all named slots -->
    <slot v-for="slot in Object.keys(slots)" :slot="slot" :name="slot" />
    <!-- Pass on all scoped slots -->
    <template
      v-for="slot in Object.keys($scopedSlots)"
      :slot="slot"
      slot-scope="scope"
    >
      <slot
        :name="slot"
        v-bind="
          // @ts-ignore
          scope
        "
      />
    </template>
  </v-text-field>
</template>

<script lang="ts">
export default {
  inheritAttrs: false
};
</script>

<script setup lang="ts">
import Cleave from 'cleave.js';
import { useListeners } from 'vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const props = defineProps({
  integer: { required: false, type: Boolean, default: false },
  value: { required: false, type: String, default: '' }
});

const emit = defineEmits<{ (e: 'input', value: string): void }>();
/**
 * When this component is used, prop [type] shouldn't be passed,
 * because it will break the Cleave.js functionality.
 * It should only accept number, thousandSeparator, and decimalSeparator as input.
 */
const attrs = useAttrs();
const slots = useSlots();
const listeners = useListeners();

const { integer, value } = toRefs(props);
const { thousandSeparator, decimalSeparator } = storeToRefs(
  useFrontendSettingsStore()
);

const textInput = ref(null);
const cleave = ref<Cleave | null>(null);
const currentValue = ref(get(value)?.replace('.', get(decimalSeparator)));

const onValueChanged = ({
  target
}: {
  target: { rawValue: string; value: string };
}) => {
  const value = target.rawValue;
  set(currentValue, target.value);
  emit('input', value);
};

const filteredListeners = (listeners: any) => {
  return { ...listeners, input: () => {} };
};

watch(value, value => {
  const clv = get(cleave);
  const rawValue = clv?.getRawValue();
  const formattedValue = value.replace('.', get(decimalSeparator));

  if (rawValue !== value) {
    set(currentValue, formattedValue);
    clv?.setRawValue(formattedValue);
  }
});

onMounted(() => {
  const inputWrapper = get(textInput) as any;
  const input = inputWrapper.$el.querySelector('input') as HTMLElement;

  set(
    cleave,
    new Cleave(input, {
      numeral: true,
      delimiter: get(thousandSeparator),
      numeralDecimalMark: get(decimalSeparator),
      numeralDecimalScale: get(integer) ? 0 : 100,
      onValueChanged
    })
  );
});
</script>
