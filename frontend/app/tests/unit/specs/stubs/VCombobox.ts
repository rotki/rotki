const VComboboxStub = {
  template: `
    <div>
      <div>
        <input :value="modelValue" class="input-value" type="text" @input="$emit('update:model-value', $event.value)">
      </div>
      <div class="selections">
        <span v-for="item in items">
          {{ item }}
        </span>
      </div>
    </div>
  `,
  props: {
    modelValue: { type: String },
    items: { type: Array<any> },
  },
};

export default VComboboxStub;
