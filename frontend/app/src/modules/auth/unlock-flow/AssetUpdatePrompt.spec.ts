import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AssetUpdatePrompt from './AssetUpdatePrompt.vue';
import '@test/i18n';

function mountPrompt(local = 37, remote = 42): VueWrapper<InstanceType<typeof AssetUpdatePrompt>> {
  return mount(AssetUpdatePrompt, { props: { versions: { changes: 5, local, remote, upToVersion: remote } } });
}

async function openOptions(wrapper: VueWrapper): Promise<void> {
  await wrapper.get('[data-testid=asset-update-options-toggle]').trigger('click');
}

async function check(wrapper: VueWrapper, testId: string): Promise<void> {
  await wrapper.get(`[data-testid=${testId}] input`).setValue(true);
}

describe('modules/auth/unlock-flow/AssetUpdatePrompt', () => {
  it('should state the versions and the change count', () => {
    const wrapper = mountPrompt();

    expect(wrapper.get('[data-testid=stage-subtitle]').text()).toBe('unlock_flow.asset_update.prompt.subtitle::37, 42');
    expect(wrapper.get('[data-testid=asset-update-changes]').text()).toBe('unlock_flow.asset_update.prompt.changes::5');
  });

  it('should keep the options folded until asked', async () => {
    const wrapper = mountPrompt();
    expect(wrapper.find('[data-testid=asset-update-options]').exists()).toBe(false);

    await openOptions(wrapper);

    expect(wrapper.find('[data-testid=asset-update-options]').exists()).toBe(true);
  });

  it('should confirm the latest version by default', async () => {
    const wrapper = mountPrompt();
    await wrapper.get('[data-testid=asset-update-confirm]').trigger('click');

    expect(wrapper.emitted('confirm')).toEqual([[{ always: false, upToVersion: 42 }]]);
  });

  it('should confirm a partial update clamped to the pending range', async () => {
    const wrapper = mountPrompt();
    await openOptions(wrapper);
    await check(wrapper, 'asset-update-partial');
    const field = wrapper.get('[data-testid=asset-update-up-to] input');

    await field.setValue('40');
    await wrapper.get('[data-testid=asset-update-confirm]').trigger('click');
    await field.setValue('99');
    await wrapper.get('[data-testid=asset-update-confirm]').trigger('click');
    await field.setValue('12');
    await wrapper.get('[data-testid=asset-update-confirm]').trigger('click');

    expect(wrapper.emitted('confirm')).toEqual([[{ always: false, upToVersion: 40 }], [{ always: false, upToVersion: 42 }], [{ always: false, upToVersion: 38 }]]);
  });

  it('should ask to apply later updates automatically when chosen', async () => {
    const wrapper = mountPrompt();
    await check(wrapper, 'asset-update-always');
    await wrapper.get('[data-testid=asset-update-confirm]').trigger('click');

    expect(wrapper.emitted('confirm')).toEqual([[{ always: true, upToVersion: 42 }]]);
  });

  it('should not offer a partial update for a single pending version', async () => {
    const wrapper = mountPrompt(41, 42);
    await openOptions(wrapper);

    expect(wrapper.find('[data-testid=asset-update-partial]').exists()).toBe(false);
  });

  it('should skip for now, or for this version once asked not to be reminded', async () => {
    const wrapper = mountPrompt();
    await wrapper.get('[data-testid=asset-update-skip]').trigger('click');
    await openOptions(wrapper);
    await check(wrapper, 'asset-update-remember');

    expect(wrapper.get('[data-testid=asset-update-skip]').text()).toBe('unlock_flow.asset_update.prompt.actions.skip_version');
    await wrapper.get('[data-testid=asset-update-skip]').trigger('click');

    expect(wrapper.emitted('skip')).toEqual([[false], [true]]);
  });
});
