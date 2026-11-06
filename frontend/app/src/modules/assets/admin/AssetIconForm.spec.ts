import { createCustomPinia } from '@test/utils/create-pinia';
import { mockUseNotifications } from '@test/utils/mocks/notifications';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetIconForm from '@/modules/assets/admin/AssetIconForm.vue';
import '@test/i18n';

const { notifyError, refreshIcon, uploadIcon } = vi.hoisted(() => ({
  notifyError: vi.fn<(title: string, message: string) => void>(),
  refreshIcon: vi.fn<(identifier: string) => Promise<void>>(),
  uploadIcon: vi.fn<(identifier: string, file: File) => Promise<void>>(),
}));

vi.mock('@/modules/assets/api/use-asset-icon-api', () => ({
  useAssetIconApi: (): Record<string, unknown> => ({ refreshIcon, setIcon: vi.fn(), uploadIcon }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () =>
  mockUseNotifications({ notifyError }));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): { getPath: () => undefined } => ({ getPath: (): undefined => undefined }),
}));

function mountForm(): VueWrapper<InstanceType<typeof AssetIconForm>> {
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
    uploadIcon.mockReset();
    notifyError.mockReset();
  });

  it('should name a failed refresh under the icon, and refresh again from there', async () => {
    refreshIcon.mockRejectedValueOnce(new Error('icon source down'));
    const wrapper = mountForm();
    await clickRefresh(wrapper);

    const strip = wrapper.find('[data-testid=asset-icon-refresh-error]');
    expect(strip.text()).toContain('icon source down');
    await strip.find('[data-testid=failure-strip-retry]').trigger('click');
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

  it('should toast a failed icon upload, since the dialog has closed by then', async () => {
    uploadIcon.mockRejectedValueOnce(new Error('too large'));
    const wrapper = mountForm();
    wrapper.findComponent({ name: 'RuiFileUpload' }).vm.$emit('update:modelValue', new File(['x'], 'icon.png', { type: 'image/png' }));
    await flushPromises();

    await wrapper.vm.saveIcon('ETH');

    expect(uploadIcon).toHaveBeenCalledWith('ETH', expect.any(File));
    expect(notifyError).toHaveBeenCalledExactlyOnceWith('asset_form.icon_upload.title', 'asset_form.icon_upload.description::too large');
  });

  it('should not toast an icon upload that worked', async () => {
    uploadIcon.mockResolvedValueOnce(undefined);
    const wrapper = mountForm();
    wrapper.findComponent({ name: 'RuiFileUpload' }).vm.$emit('update:modelValue', new File(['x'], 'icon.png', { type: 'image/png' }));
    await flushPromises();

    await wrapper.vm.saveIcon('ETH');

    expect(uploadIcon).toHaveBeenCalledOnce();
    expect(notifyError).not.toHaveBeenCalled();
  });
});
