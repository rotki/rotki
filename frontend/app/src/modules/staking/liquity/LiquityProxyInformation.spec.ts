import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import LiquityProxyInformation from '@/modules/staking/liquity/LiquityProxyInformation.vue';

const HashLinkStub = defineComponent({
  name: 'HashLinkStub',
  props: { text: { default: '', type: String } },
  template: '<div data-testid="hash-link">{{ text }}</div>',
});

const DividerStub = defineComponent({
  name: 'DividerStub',
  template: '<hr data-testid="divider" />',
});

describe('modules/staking/liquity/LiquityProxyInformation', () => {
  let wrapper: VueWrapper<InstanceType<typeof LiquityProxyInformation>>;

  function mountComponent(proxyInformation: Record<string, string[]>): VueWrapper<InstanceType<typeof LiquityProxyInformation>> {
    return mount(LiquityProxyInformation, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          HashLink: HashLinkStub,
          RuiDivider: DividerStub,
          // The contents live in a menu that only renders once opened.
          RuiMenu: { template: '<div><slot /></div>' },
        },
      },
      props: { proxyInformation },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should link the owner and each of its proxies', () => {
    wrapper = mountComponent({ '0xaaa': ['0xproxy1', '0xproxy2'] });

    const links = wrapper.findAllComponents(HashLinkStub).map(item => item.props('text'));
    expect(links).toEqual(['0xaaa', '0xproxy1', '0xproxy2']);
  });

  it('should separate owners with a divider, but not trail one after the last', () => {
    wrapper = mountComponent({ '0xaaa': ['0xproxy1'], '0xbbb': ['0xproxy2'] });

    expect(wrapper.findAllComponents(DividerStub)).toHaveLength(1);
  });

  it('should show no divider for a single owner', () => {
    wrapper = mountComponent({ '0xaaa': ['0xproxy1'] });

    expect(wrapper.findComponent(DividerStub).exists()).toBe(false);
  });

  it('should show one divider fewer than the number of owners', () => {
    wrapper = mountComponent({ '0xaaa': ['0xp1'], '0xbbb': ['0xp2'], '0xccc': ['0xp3'] });

    expect(wrapper.findAllComponents(DividerStub)).toHaveLength(2);
  });

  it('should render nothing for an empty record', () => {
    wrapper = mountComponent({});

    expect(wrapper.findComponent(HashLinkStub).exists()).toBe(false);
  });
});
