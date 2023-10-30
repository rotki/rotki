const RuiTooltipStub = {
  setup() {
    const open = ref(false);

    return { open };
  },
  template: `
    <div @mouseover="open = true" @mouseleave="open = false">
      <div>
        <slot name="activator"/>
      </div>
      <slot v-if="open" />
    </div>
  `
};

export default RuiTooltipStub;
