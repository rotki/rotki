import type { BankManifest } from '@/modules/banks/types';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent, nextTick } from 'vue';
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
    noFilter: { default: false, type: Boolean },
    options: { default: (): unknown[] => [], type: Array },
    searchInput: { default: '', type: String },
    textAttr: { default: '', type: String },
  },
  emits: ['update:searchInput'],
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
    expect(autocomplete.props('textAttr')).toBe('name');
    expect(autocomplete.props('noFilter')).toBe(true);
    expect(options).toHaveLength(fintsBanks.length + 2);
    expect(options.some(option => Reflect.get(new Object(option), 'id') === 'connector:qonto')).toBe(true);
    expect(Reflect.get(new Object(options.at(-1)), 'kind')).toBe('fints-manual');
  });

  it('should prioritize bank-name matches over partial name and location matches', async () => {
    const wrapper = mount(BankConnectionPicker, {
      global: { stubs: { BankLabel: true, RuiAutoComplete: AutoCompleteStub } },
      props: { errorMessages: [], manifests: [manifest] },
    });
    const autocomplete = wrapper.findComponent(AutoCompleteStub);

    autocomplete.vm.$emit('update:searchInput', 'ING');
    await nextTick();

    const options = autocomplete.props('options') ?? [];
    expect(Reflect.get(new Object(options[0]), 'name')).toBe('ING-DiBa');
    expect(options.some(option => Reflect.get(new Object(option), 'bank')?.city === 'Göttingen')).toBe(true);
  });

  it('should retain location and exact BLZ searches', async () => {
    const wrapper = mount(BankConnectionPicker, {
      global: { stubs: { BankLabel: true, RuiAutoComplete: AutoCompleteStub } },
      props: { errorMessages: [], manifests: [manifest] },
    });
    const autocomplete = wrapper.findComponent(AutoCompleteStub);

    autocomplete.vm.$emit('update:searchInput', 'Frankfurt');
    await nextTick();
    expect((autocomplete.props('options') ?? []).some(option =>
      Reflect.get(new Object(option), 'bank')?.bankCodes.includes('50010517'))).toBe(true);

    autocomplete.vm.$emit('update:searchInput', '50010517');
    await nextTick();
    expect(Reflect.get(new Object((autocomplete.props('options') ?? [])[0]), 'name')).toBe('ING-DiBa');
  });
});
