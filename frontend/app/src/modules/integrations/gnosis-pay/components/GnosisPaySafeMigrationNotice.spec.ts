import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import GnosisPaySafeMigrationNotice from '@/modules/integrations/gnosis-pay/components/GnosisPaySafeMigrationNotice.vue';

function mountNotice(failure?: string): VueWrapper {
  return mount(GnosisPaySafeMigrationNotice, {
    global: { stubs: { AccountDisplay: true, I18nT: true } },
    props: { failure, keypath: 'external_services.gnosispay.safe_migration.missing_new' },
  });
}

describe('gnosisPaySafeMigrationNotice', () => {
  it('should name a failed add inside the notice', () => {
    const strip = mountNotice('node unreachable').find('[data-testid=gnosis-pay-safe-add-failure]');

    expect(strip.text()).toContain('external_services.gnosispay.safe_migration.add_error');
    expect(strip.text()).toContain('node unreachable');
  });

  it('should add again from the failure retry', async () => {
    const wrapper = mountNotice('node unreachable');

    await wrapper.find('[data-testid=failure-strip-retry]').trigger('click');

    expect(wrapper.emitted('add')).toHaveLength(1);
  });

  it('should name no failure while there is none', () => {
    expect(mountNotice().find('[data-testid=gnosis-pay-safe-add-failure]').exists()).toBe(false);
  });
});
