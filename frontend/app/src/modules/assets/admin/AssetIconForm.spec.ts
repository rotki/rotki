import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetIconForm from '@/modules/assets/admin/AssetIconForm.vue';
import '@test/i18n';

const { refreshIcon } = vi.hoisted(() => ({ refreshIcon: vi.fn<(identifier: string) => Promise<void>>() }));

vi.mock('@/modules/assets/api/use-asset-icon-api', () => ({
  useAssetIconApi: (): Record<string, unknown> => ({ refreshIcon, setIcon: vi.fn(), uploadIcon: vi.fn() }),
}));

function mountForm(): VueWrapper {
  const pinia = createCustomPinia();
  setActivePinia(pinia);
  return mount(AssetIconForm, {
    global: {
      plugins: [pinia],
      provide: libraryDefaults,
      stubs: { AppImage: true, AssetIcon: true, RuiFileUpload: true, RuiTooltip: { template: '<div><slot name="activator" /></div>' } },
    },
    props: { identifier: 'ETH', refreshable: true },
  });
}

async function clickRefresh(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('[data-testid=asset-icon-refresh]').trigger('click');
  await flushPromises();
}

describe('assetIconForm', () => {
  beforeEach(() => {
    refreshIcon.mockReset();
  });

  it('should name a failed refresh under the icon, and refresh again from there', async () => {
    refreshIcon.mockRejectedValueOnce(new Error('icon source down'));
    const wrapper = mountForm();
    await clickRefresh(wrapper);

    const strip = wrapper.find('[data-testid=asset-icon-refresh-error]');
    expect(strip.text()).toContain('icon source down');
    await strip.find('[data-testid=table-failure-strip-retry]').trigger('click');
    await flushPromises();

    expect(refreshIcon).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-testid=asset-icon-refresh-error]').exists()).toBe(false);
  });

  it('should show no failure after a refresh that worked', async () => {
    refreshIcon.mockResolvedValue(undefined);
    const wrapper = mountForm();

    await clickRefresh(wrapper);

    expect(refreshIcon).toHaveBeenCalledWith('ETH');
    expect(wrapper.find('[data-testid=asset-icon-refresh-error]').exists()).toBe(false);
  });
});
