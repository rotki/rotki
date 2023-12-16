export const RuiAutoCompleteStub = {
  template: `
    <div :data-cy="dataCy" :disabled="disabled" v-bind="$attrs">
      <div>
        <input :value="modelValue" class="input-value" type="text" @input="$emit('update:model-value', $event.value)">
      </div>
      <div class="selections">
        <span v-for="item in options">
          {{ item[keyProp] ?? item }}
        </span>
      </div>
      <div v-if="error || message" class="details">
        {{ error || message }}
      </div>
    </div>
  `,
  props: {
    modelValue: { type: [String, Array<string>] },
    successMessages: { type: [String, Array<string>], default: () => [] },
    errorMessages: { type: [String, Array<string>], default: () => [] },
    options: { type: Array<any> },
    keyProp: { type: String },
    dataCy: { type: String, default: '' },
    disabled: { type: Boolean, default: false },
  },
  inheritAttrs: false,
  computed: {
    message(): string {
      const m: string | string[] = this.successMessages;
      return Array.isArray(m) ? m[0] : m;
    },
    error(): string {
      const m: string | string[] = this.errorMessages;
      return Array.isArray(m) ? m[0] : m;
    },
  },
};
