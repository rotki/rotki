const VAutocompleteStub = {
  template: `
    <div>
      <div>
        <input :value="value?.toString()" class="input-value" type="text" @input="$emit('input', $event.value)">
      </div>
      <div class="selections">
        <span v-for="item in items">
          {{ item[itemValue] ?? item }}
        </span>
      </div>
      <div v-if="error || message" class="details">
        {{ error || message }}
      </div>
    </div>
  `,
  props: {
    value: { type: [String, Array<string>] },
    successMessages: { type: [String, Array<string>], default: [] },
    errorMessages: { type: [String, Array<string>], default: [] },
    items: { type: Array<any> },
    itemValue: { type: String },
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

export default VAutocompleteStub;
