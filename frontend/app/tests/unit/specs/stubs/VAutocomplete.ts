const VAutocompleteStub = {
  template: `
    <div>
      <div>
        <input :value="modelValue" class="input-value" type="text" @input="$emit('update:model-value', $event.value)">
      </div>
      <div class="selections">
        <span v-for="item in items">
          {{ item[itemValue] ?? item }}
        </span>
      </div>
    </div>
  `,
  props: {
    modelValue: { type: String },
    items: { type: Array<any> },
    itemValue: { type: String },
  },
};

export default VAutocompleteStub;
