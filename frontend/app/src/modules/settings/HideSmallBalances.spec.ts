import { DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import HideSmallBalances from '@/modules/settings/HideSmallBalances.vue';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

const { updateFrontendSetting } = vi.hoisted(() => ({
  updateFrontendSetting: vi.fn(),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): { updateFrontendSetting: typeof updateFrontendSetting } => ({ updateFrontendSetting }),
}));

type HideSmallBalancesInstance = InstanceType<typeof HideSmallBalances>;

describe('settings/HideSmallBalances.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<HideSmallBalancesInstance>;

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    updateFrontendSetting.mockReset();
    updateFrontendSetting.mockResolvedValue(undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  /** The controls live in a menu, so it has to be opened before anything is reachable. */
  async function createWrapper(): Promise<VueWrapper<HideSmallBalancesInstance>> {
    const mounted = mount(HideSmallBalances, {
      attachTo: document.body,
      global: {
        plugins: [pinia],
      },
      props: {
        source: BalanceSource.BLOCKCHAIN,
      },
    });

    await mounted.find('button').trigger('click');
    await vi.waitUntil(() => document.body.querySelector('[data-testid=hide-small-balances-apply]') !== null);
    return mounted;
  }

  /** The menu content is teleported out of the wrapper, so it is reached through the document. */
  function inBody<T extends Element>(selector: string): DOMWrapper<T> {
    const element = document.body.querySelector<T>(selector);
    assert(element, `${selector} is not rendered`);
    return new DOMWrapper(element);
  }

  function thresholdInput(): DOMWrapper<HTMLInputElement> {
    return inBody<HTMLInputElement>('[data-testid=hide-small-balances-threshold] input');
  }

  function hideToggle(): DOMWrapper<HTMLInputElement> {
    return inBody<HTMLInputElement>('[data-testid=hide-small-balances-toggle] input');
  }

  function applyButton(): DOMWrapper<HTMLButtonElement> {
    return inBody<HTMLButtonElement>('[data-testid=hide-small-balances-apply]');
  }

  function hasError(): boolean {
    return document.body.querySelector('[data-testid=hide-small-balances-threshold] .text-rui-error') !== null;
  }

  it('should apply the threshold to every source by default', async () => {
    wrapper = await createWrapper();

    await hideToggle().setValue(true);
    await thresholdInput().setValue('5');
    await applyButton().trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).toHaveBeenCalledWith({
      balanceValueThreshold: {
        [BalanceSource.BLOCKCHAIN]: '5',
        [BalanceSource.EXCHANGES]: '5',
        [BalanceSource.MANUAL]: '5',
      },
    });
  });

  it('should clear every threshold when hiding is switched off', async () => {
    wrapper = await createWrapper();

    await applyButton().trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ balanceValueThreshold: {} });
  });

  it('should reject a negative threshold', async () => {
    wrapper = await createWrapper();

    await hideToggle().setValue(true);
    await thresholdInput().setValue('-1');

    expect(hasError()).toBe(true);

    await applyButton().trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should reject an empty threshold', async () => {
    wrapper = await createWrapper();

    await hideToggle().setValue(true);
    await thresholdInput().setValue('');

    expect(hasError()).toBe(true);

    await applyButton().trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });
});
