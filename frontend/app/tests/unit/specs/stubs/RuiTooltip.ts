const RuiTooltipStub = {
  setup() {
    const open = ref(false);

    return { open };
  },
  template:
    '<div><div @mouseover="open = true" @mouseleave="open = false"><slot name="activator"></slot></div><slot v-if="open" /></div>'
};

export default RuiTooltipStub;
