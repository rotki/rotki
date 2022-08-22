<template>
  <v-text-field
    ref="textInput"
    v-model="currentValue"
    v-bind="$attrs"
    v-on="filteredListeners($listeners)"
  >
    <!-- Pass on all named slots -->
    <slot v-for="slot in Object.keys($slots)" :slot="slot" :name="slot" />
    <!-- Pass on all scoped slots -->
    <template
      v-for="slot in Object.keys($scopedSlots)"
      :slot="slot"
      slot-scope="scope"
    >
      <slot :name="slot" v-bind="scope" />
    </template>
  </v-text-field>
</template>

<script lang="ts">
import { get, set } from '@vueuse/core';
import Cleave from 'cleave.js';
import { storeToRefs } from 'pinia';
import { defineComponent, onMounted, ref, toRefs, watch } from 'vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

/**
 * When this component is used, prop [type] shouldn't be passed,
 * because it will break the Cleave.js functionality.
 * It should only accept number, thousandSeparator, and decimalSeparator as input.
 */
export default defineComponent({
  name: 'AmountInput',
  inheritAttrs: false,
  props: {
    integer: { required: false, type: Boolean, default: false },
    value: { required: false, type: String, default: '' }
  },
  emits: ['input'],
  setup(props, { emit }) {
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
      let value = target.rawValue;
      set(currentValue, target.value);
      emit('input', value);
    };

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

    watch(value, value => {
      const rawValue = get(cleave)?.getRawValue();
      const formattedValue = value.replace('.', get(decimalSeparator));

      if (rawValue !== value) {
        set(currentValue, formattedValue);
        get(cleave)?.setRawValue(formattedValue);
      }
    });

    const focus = () => {
      const inputWrapper = get(textInput) as any;
      if (inputWrapper) {
        inputWrapper.focus();
      }
    };

    const filteredListeners = (listeners: any) => {
      return { ...listeners, input: () => {} };
    };

    return {
      focus,
      currentValue,
      textInput,
      filteredListeners
    };
  }
});
</script>
