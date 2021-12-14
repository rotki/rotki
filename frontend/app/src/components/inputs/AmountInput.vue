<template>
  <v-text-field
    ref="textInput"
    v-model="currentValue"
    v-bind="$attrs"
    v-on="$listeners"
  />
</template>

<script lang="ts">
import {
  watch,
  defineComponent,
  onMounted,
  ref,
  toRefs,
  computed
} from '@vue/composition-api';
import Cleave from 'cleave.js';
import { useStore } from '@/store/utils';

/**
 * When this component is used, prop [type] shouldn't be passed,
 * because it will break the Cleave.js functionality.
 * It should only accept number, thousandSeparator, and decimalSeparator as input.
 */
export default defineComponent({
  name: 'AmountInput',
  inheritAttrs: false,
  props: {
    value: { required: true, type: String }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { value } = toRefs(props);

    const textInput = ref(null);

    const currentValue = ref(value.value);

    const cleave = ref<Cleave | null>(null);

    const store = useStore();
    const thousandSeparator = computed<string>(
      () => store.getters['settings/thousandSeparator']
    );

    const decimalSeparator = computed<string>(
      () => store.getters['settings/decimalSeparator']
    );

    const onValueChanged = ({
      target
    }: {
      target: { rawValue: string; value: string };
    }) => {
      let value = target.rawValue;
      currentValue.value = target.value;
      emit('input', value);
    };

    onMounted(() => {
      const inputWrapper = textInput.value as any;
      const input = inputWrapper.$el.querySelector('input') as HTMLElement;

      cleave.value = new Cleave(input, {
        numeral: true,
        delimiter: thousandSeparator.value,
        numeralDecimalMark: decimalSeparator.value,
        numeralDecimalScale: 100,
        onValueChanged
      });
    });

    watch(value, () => {
      currentValue.value = value.value;
      cleave.value?.setRawValue(value.value);
    });

    const focus = () => {
      const inputWrapper = textInput.value as any;
      if (inputWrapper) {
        inputWrapper.focus();
      }
    };

    return {
      focus,
      currentValue,
      textInput
    };
  }
});
</script>
