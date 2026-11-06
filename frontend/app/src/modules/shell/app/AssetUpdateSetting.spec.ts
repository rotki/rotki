import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AssetUpdateSetting from '@/modules/shell/app/AssetUpdateSetting.vue';

function mountSetting(upToDate: boolean): VueWrapper {
  return mount(AssetUpdateSetting, {
    global: { stubs: { SettingsItem: { template: '<div><slot /></div>' } } },
    props: { loading: false, skipped: 0, upToDate },
  });
}

describe('assetUpdateSetting', () => {
  it('should say beside the check button that the database is up to date', () => {
    expect(mountSetting(true).find('[data-testid=asset-update-up-to-date]').text()).toBe('asset_update.up_to_date');
  });

  it('should say nothing until a check found nothing newer', () => {
    expect(mountSetting(false).find('[data-testid=asset-update-up-to-date]').exists()).toBe(false);
  });
});
