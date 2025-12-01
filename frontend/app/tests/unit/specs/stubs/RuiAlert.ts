export const RuiAlertStub = {
  template: '<div data-testid="alert" :data-type="type"><slot /></div>',
  props: {
    type: { type: String },
  },
};
