import type { MaybeRefOrGetter } from 'vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { UnlockErrorKind, UnlockPhase } from '@/modules/auth/unlock-flow/use-unlock-flow';
import AssetUpdateProgress from './AssetUpdateProgress.vue';
import '@test/i18n';

const copy = vi.hoisted(() => ({ copy: vi.fn() }));

vi.mock('@/modules/core/common/use-clipboard', async () => {
  const { ref, toValue } = await import('vue');
  return {
    useCopy: (source: MaybeRefOrGetter<string>): unknown => ({
      copied: ref<boolean>(false),
      copy: async (): Promise<void> => copy.copy(toValue(source)),
    }),
  };
});

function mountProgress(phase: string, error?: { kind: string; message: string }): VueWrapper<InstanceType<typeof AssetUpdateProgress>> {
  return mount(AssetUpdateProgress, {
    props: { error: error?.message, errorKind: error?.kind, from: 37, phase, to: 42 },
  });
}

function stepStatuses(wrapper: VueWrapper): (string | undefined)[] {
  return wrapper.findAll('[data-testid=asset-update-step]').map(step => step.attributes('data-status'));
}

describe('modules/auth/unlock-flow/AssetUpdateProgress', () => {
  it('should show the run and the step it is on', () => {
    const wrapper = mountProgress(UnlockPhase.restarting);

    expect(wrapper.get('[data-testid=stage-title]').text()).toBe('unlock_flow.asset_update.progress.title.running');
    expect(wrapper.get('[data-testid=stage-subtitle]').text()).toBe('unlock_flow.asset_update.range::37, 42');
    expect(stepStatuses(wrapper)).toStrictEqual(['done', 'current', 'pending']);
    expect(wrapper.find('[data-testid=asset-update-failure]').exists()).toBe(false);
  });

  it('should report the finished update', () => {
    const wrapper = mountProgress(UnlockPhase.ready);

    expect(wrapper.get('[data-testid=stage-title]').text()).toBe('unlock_flow.asset_update.progress.title.done::42');
    expect(wrapper.attributes('data-outcome')).toBe('done');
  });

  it('should explain a failure with ways out', async () => {
    const wrapper = mountProgress(UnlockPhase.error, { kind: UnlockErrorKind.updateFailed, message: 'no space left' });

    expect(wrapper.get('[data-testid=stage-title]').text()).toBe('unlock_flow.asset_update.progress.title.failed');
    expect(wrapper.get('[data-testid=asset-update-error]').text()).toBe('no space left');
    expect(stepStatuses(wrapper)).toStrictEqual(['failed', 'pending', 'pending']);

    await wrapper.get('[data-testid=asset-update-copy]').trigger('click');
    await wrapper.get('[data-testid=asset-update-back]').trigger('click');
    await wrapper.get('[data-testid=asset-update-report]').trigger('click');

    expect(copy.copy).toHaveBeenCalledWith('no space left\nunlock_flow.asset_update.range::37, 42');
    expect(wrapper.emitted('back')).toHaveLength(1);
    expect(wrapper.emitted('report')).toHaveLength(1);
  });
});
