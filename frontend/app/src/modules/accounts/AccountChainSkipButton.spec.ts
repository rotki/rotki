import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AccountChainSkipButton from '@/modules/accounts/AccountChainSkipButton.vue';

describe('modules/accounts/AccountChainSkipButton', () => {
  function createWrapper(props: Partial<{ label: string; skipped: boolean; locked: boolean; pending: boolean }> = {}): VueWrapper {
    return mount(AccountChainSkipButton, {
      global: {
        stubs: { RuiTooltip: { template: '<div><slot name="activator" /></div>' } },
      },
      props: { chain: 'eth', label: 'skip eth', locked: false, pending: false, skipped: false, ...props },
    });
  }

  function button(wrapper: VueWrapper): ReturnType<VueWrapper['find']> {
    return wrapper.find('[data-testid=account-chain-skip]');
  }

  it('should ask to toggle when clicked', async () => {
    const wrapper = createWrapper();

    await button(wrapper).trigger('click');

    expect(wrapper.emitted('toggle')).toHaveLength(1);
  });

  it('should name what it does', () => {
    expect(button(createWrapper({ label: 'query eth again' })).attributes('aria-label')).toBe('query eth again');
  });

  it('should stay enabled while saving, so focus stays in the menu', () => {
    expect(button(createWrapper({ pending: true })).attributes('disabled')).toBeUndefined();
  });

  it('should be closed off for a chain switched off whole', () => {
    expect(button(createWrapper({ locked: true })).attributes('disabled')).toBeDefined();
  });
});
