const VSelectStub = {
  template: `
    <div>
      <input :value="modelValue" class="input" type="text" @input="$emit('update:model-value', $event.value)">
    </div>
  `,
  props: {
    modelValue: { type: String },
  },
};

export default VSelectStub;
