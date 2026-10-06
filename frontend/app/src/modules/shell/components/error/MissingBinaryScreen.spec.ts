import { BinaryPlatform, BinaryStatus, type UnusableBinary } from '@shared/starling/binary-types';
import { QUARANTINED_COLIBRI } from '@test/fixtures/unusable-binary';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import MissingBinaryScreen from './MissingBinaryScreen.vue';

const closeApp = vi.fn<() => Promise<void>>();

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): { closeApp: typeof closeApp } => ({ closeApp }),
}));

function mountScreen(binary: UnusableBinary = QUARANTINED_COLIBRI): VueWrapper {
  return mount(MissingBinaryScreen, { props: { binary } });
}

describe('missingBinaryScreen', () => {
  it('should name the component and the path it was expected at', () => {
    const text = mountScreen().text();

    expect(text).toContain('missing_binary.title.missing');
    expect(text).toContain(QUARANTINED_COLIBRI.path);
  });

  it('should say which component failed before explaining why, so the card comes before the cause and the steps', () => {
    const text = mountScreen().text();

    expect(text.indexOf(QUARANTINED_COLIBRI.path)).toBeLessThan(text.indexOf('missing_binary.cause.missing'));
    expect(text.indexOf('missing_binary.cause.missing')).toBeLessThan(text.indexOf('missing_binary.steps.update_definitions'));
  });

  it('should list the recovery steps in order', () => {
    const steps = mountScreen().findAll('li').map(step => step.text());

    expect(steps).toStrictEqual([
      'missing_binary.steps.update_definitions',
      'missing_binary.steps.restore',
      'missing_binary.steps.exclude',
      'missing_binary.steps.reinstall',
    ]);
  });

  it('should show only the restart instruction for an update installed while rotki ran', () => {
    const wrapper = mountScreen({ ...QUARANTINED_COLIBRI, status: BinaryStatus.REPLACED });

    expect(wrapper.findAll('li')).toHaveLength(0);
    expect(wrapper.find('[data-testid=missing-binary-recovery]').text()).toBe('missing_binary.recovery.restart');
  });

  it('should offer only to terminate, since the file is still gone', async () => {
    const wrapper = mountScreen({ ...QUARANTINED_COLIBRI, platform: BinaryPlatform.WINDOWS });

    await wrapper.find('[data-testid=missing-binary-terminate]').trigger('click');

    expect(closeApp).toHaveBeenCalledOnce();
  });
});
