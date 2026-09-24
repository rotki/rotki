import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import DetectEvmAccounts from '@/modules/accounts/balances/DetectEvmAccounts.vue';
import { useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';

const h = vi.hoisted(() => ({
  detectEvmAccounts: vi.fn(),
}));

vi.mock('@/modules/accounts/use-evm-account-detection', () => ({
  useEvmAccountDetection: vi.fn(() => ({ detectEvmAccounts: h.detectEvmAccounts })),
}));

describe('modules/accounts/balances/DetectEvmAccounts', () => {
  let wrapper: VueWrapper;

  function createWrapper(): VueWrapper {
    return mount(DetectEvmAccounts, {
      global: {
        stubs: {
          RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' },
        },
      },
    });
  }

  function label(): string {
    return wrapper.find('[data-testid=detect-evm-accounts-label]').text();
  }

  async function finishRun(accounts: { address: string; chain: string }[]): Promise<void> {
    useDetectedAccountsStore().setLastRun(accounts);
    await nextTick();
  }

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should run detection on click', async () => {
    wrapper = createWrapper();

    await wrapper.find('[data-testid=detect-evm-accounts]').trigger('click');

    expect(h.detectEvmAccounts).toHaveBeenCalledOnce();
  });

  it('should carry its idle label before a run has finished', () => {
    wrapper = createWrapper();

    expect(label()).toBe('blockchain_balances.evm_detection.title');
  });

  it('should count the chains a run added, not the address and chain pairs', async () => {
    wrapper = createWrapper();

    await finishRun([
      { address: '0xabc', chain: 'eth' },
      { address: '0xdef', chain: 'eth' },
      { address: '0xabc', chain: 'base' },
    ]);

    expect(label()).toBe('blockchain_balances.evm_detection.found::2');
  });

  it('should say when a run found nothing', async () => {
    wrapper = createWrapper();

    await finishRun([]);

    expect(label()).toBe('blockchain_balances.evm_detection.none');
  });

  it('should return to its idle label once the outcome has been shown', async () => {
    vi.useFakeTimers();
    wrapper = createWrapper();
    await finishRun([]);

    vi.advanceTimersByTime(4000);
    await nextTick();

    expect(label()).toBe('blockchain_balances.evm_detection.title');
  });

  it('should drop the previous outcome as soon as a new run starts', async () => {
    wrapper = createWrapper();
    await finishRun([{ address: '0xabc', chain: 'eth' }]);

    useDetectedAccountsStore().setLastRun(undefined);
    await nextTick();

    expect(label()).toBe('blockchain_balances.evm_detection.title');
  });

  it('should reserve the width of every label, so an outcome never resizes the button', async () => {
    wrapper = createWrapper();

    const reserved = wrapper.findAll('[aria-hidden=true]').map(element => element.text());

    expect(reserved).toEqual([
      'blockchain_balances.evm_detection.title',
      'blockchain_balances.evm_detection.none',
      'blockchain_balances.evm_detection.found::99',
    ]);
  });
});
