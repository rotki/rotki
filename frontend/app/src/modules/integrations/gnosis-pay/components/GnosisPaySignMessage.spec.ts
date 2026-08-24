/**
 * Seam: this component renders step 3 of the Gnosis Pay auth card. It promises its parent that
 * - the domain notice appears only on an injected-wallet path, where the wallet has a page origin
 *   to compare against (the packaged app's bridge page, or a self-hosted deployment's own host),
 * - the sign button is swapped for the chain-switch button when the wallet is on the wrong chain,
 * - clicking either one emits, rather than acting.
 */
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import GnosisPaySignMessage from './GnosisPaySignMessage.vue';

const NOTICE = '[data-testid=siwe-domain-notice]';

describe('gnosisPaySignMessage', () => {
  const wrappers: VueWrapper[] = [];

  function mountComponent(props: Partial<InstanceType<typeof GnosisPaySignMessage>['$props']> = {}): VueWrapper {
    const wrapper = mount(GnosisPaySignMessage, {
      props: {
        isInjectedWallet: true,
        isOnGnosisChain: true,
        isWalletConnected: true,
        primaryActionDisabled: false,
        signingInProgress: false,
        switchingNetwork: false,
        ...props,
      },
    });
    wrappers.push(wrapper);
    return wrapper;
  }

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  it('should show the domain notice on an injected-wallet path', () => {
    expect(mountComponent().find(NOTICE).exists()).toBe(true);
  });

  it('should hide the domain notice on the walletconnect path', () => {
    // Negative control for the gate: over WalletConnect there is no origin to mismatch, so the
    // notice would be noise. A test that only asserts it renders proves nothing about the gate.
    expect(mountComponent({ isInjectedWallet: false }).find(NOTICE).exists()).toBe(false);
  });

  it('should emit sign-in when the sign button is clicked', async () => {
    const wrapper = mountComponent();
    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('sign-in')).toHaveLength(1);
  });

  it('should offer the chain switch instead of signing when on the wrong chain', async () => {
    const wrapper = mountComponent({ isOnGnosisChain: false });
    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('switch-to-gnosis')).toHaveLength(1);
    expect(wrapper.emitted('sign-in')).toBeUndefined();
  });
});
