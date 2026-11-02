import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import FinTsBankPicker from '@/modules/banks/components/FinTsBankPicker.vue';
import '@test/i18n';

const AutoCompleteStub = defineComponent({
  props: {
    keyAttr: { default: '', type: String },
    options: { default: (): unknown[] => [], type: Array },
    textAttr: { default: '', type: String },
  },
  template: '<div />',
});

describe('finTSBankPicker', () => {
  it('should provide searchable, BLZ-keyed options to the autocomplete', () => {
    const wrapper = mount(FinTsBankPicker, {
      global: { stubs: { RuiAutoComplete: AutoCompleteStub } },
    });
    const autocomplete = wrapper.findComponent(AutoCompleteStub);
    const options = autocomplete.props('options') ?? [];
    expect(autocomplete.props('keyAttr')).toBe('blz');
    expect(autocomplete.props('textAttr')).toBe('searchText');
    expect(options).toHaveLength(6);
    expect(options.every(option => typeof Reflect.get(new Object(option), 'searchText') === 'string')).toBe(true);
  });
});
