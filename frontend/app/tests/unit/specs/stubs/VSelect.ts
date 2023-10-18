const VSelectStub = {
  template: `
    <div>
      <input :value="value" class="input" type="text" @input="$emit('input', $event.value)">
    </div>
  `,
  props: {
    value: { type: String }
  }
};

export default VSelectStub;
