import type { BankManifest } from '@/modules/banks/types';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import BankConnectionPicker from '@/modules/banks/components/BankConnectionPicker.vue';
import { fintsBanks } from '@/modules/banks/fints-bank-directory';
import '@test/i18n';

const manifest: BankManifest = {
  accessTier: 'official api',
  authFlow: [],
  capabilities: [],
  displayName: 'Qonto',
  docsUrl: '',
  location: 'qonto',
  maintainer: 'rotki',
  secrets: [],
  setupNotes: [],
  version: '1',
};

const AutoCompleteStub = defineComponent({
  props: {
    keyAttr: { default: '', type: String },
    options: { default: (): unknown[] => [], type: Array },
    textAttr: { default: '', type: String },
  },
  template: '<div />',
});

describe('bankConnectionPicker', () => {
  it('should combine dedicated connectors, every FinTS institution, and the manual fallback', () => {
    const wrapper = mount(BankConnectionPicker, {
      global: { stubs: { BankLabel: true, RuiAutoComplete: AutoCompleteStub } },
      props: { errorMessages: [], manifests: [manifest] },
    });
    const autocomplete = wrapper.findComponent(AutoCompleteStub);
    const options = autocomplete.props('options') ?? [];
    expect(autocomplete.props('keyAttr')).toBe('id');
    expect(autocomplete.props('textAttr')).toBe('searchText');
    expect(options).toHaveLength(fintsBanks.length + 2);
    expect(options.some(option => Reflect.get(new Object(option), 'id') === 'connector:qonto')).toBe(true);
    expect(Reflect.get(new Object(options.at(-1)), 'kind')).toBe('fints-manual');
  });
});
