import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import UnmatchedResolutionStrip from '@/modules/history/events/UnmatchedResolutionStrip.vue';

describe('modules/history/events/UnmatchedResolutionStrip', () => {
  let wrapper: VueWrapper<InstanceType<typeof UnmatchedResolutionStrip>> | undefined;

  function mountStrip(props: { message: string; loading?: boolean }): VueWrapper<InstanceType<typeof UnmatchedResolutionStrip>> {
    wrapper = mount(UnmatchedResolutionStrip, { props });
    return wrapper;
  }

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should render the message it is given', () => {
    const strip = mountStrip({ message: 'Bridge withdrawal resolved as income from an external address.' });

    expect(strip.find('[data-testid="unmatched-resolution-strip"]').text())
      .toContain('Bridge withdrawal resolved as income from an external address.');
  });

  it('should report an undo', async () => {
    const strip = mountStrip({ message: 'resolved' });

    await strip.find('[data-testid="unmatched-resolution-undo"]').trigger('click');

    expect(strip.emitted('undo')).toHaveLength(1);
    expect(strip.emitted('dismiss')).toBeUndefined();
  });

  it('should report a dismiss without undoing anything', async () => {
    const strip = mountStrip({ message: 'resolved' });

    await strip.find('[data-testid="unmatched-resolution-dismiss"]').trigger('click');

    expect(strip.emitted('dismiss')).toHaveLength(1);
    expect(strip.emitted('undo')).toBeUndefined();
  });
});
