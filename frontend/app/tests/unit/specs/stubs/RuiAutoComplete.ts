import { computed, defineComponent, type PropType } from 'vue';

export const RuiAutoCompleteStub = defineComponent({
  template: `
      <div :data-cy="dataCy" v-bind="$attrs">
        <div>
          <input
              :value="modelValue"
              class="input-value"
              type="text"
              @input="handleInput($event)"
              @paste="handlePaste($event)"
              :disabled="disabled">
        </div>
        <div class="selections">
        <span v-for="item in options" :key="item[keyProp]">
          {{ item[keyProp] ?? item }}
        </span>
        </div>
        <div v-if="error || message" class="details">
          {{ error || message }}
        </div>
      </div>
    `,
  props: {
    modelValue: { type: [String, Array] as PropType<string | string[]> },
    successMessages: { type: [String, Array] as PropType<string | string[]>, default: () => [] },
    errorMessages: { type: [String, Array] as PropType<string | string[]>, default: () => [] },
    options: { type: Array as PropType<any[]>, default: () => [] },
    keyProp: { type: String, default: '' },
    dataCy: { type: String, default: '' },
    disabled: { type: Boolean, default: false },
  },
  emits: ['update:model-value', 'paste'],
  setup(props, { emit }) {
    const message = computed<string>(() => {
      const m: string | string[] = props.successMessages;
      return Array.isArray(m) ? m[0] : m;
    });

    const error = computed<string>(() => {
      const m: string | string[] = props.errorMessages;
      return Array.isArray(m) ? m[0] : m;
    });

    const handleInput = (event: Event): void => {
      const data = (event.target as HTMLInputElement).value;
      if (Array.isArray(props.modelValue)) {
        emit('update:model-value', data.split(','));
      }
      else {
        emit('update:model-value', data);
      }
    };

    const handlePaste = (event: ClipboardEvent): void => {
      emit('paste', event);
    };

    return {
      message,
      error,
      handleInput,
      handlePaste,
    };
  },
});
