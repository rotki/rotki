import { BinaryStatus, type UnusableBinary } from '@shared/starling/binary-types';
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

    expect(text).toContain('missing_binary.missing');
    expect(text).toContain(QUARANTINED_COLIBRI.path);
  });

  it('should distinguish a file that is there but cannot be run', () => {
    const text = mountScreen({ ...QUARANTINED_COLIBRI, status: BinaryStatus.NOT_EXECUTABLE }).text();

    expect(text).toContain('missing_binary.not_executable');
    expect(text).toContain('missing_binary.header_not_executable');
    expect(text).not.toContain('missing_binary.missing');
  });

  it('should put updating definitions before restoring, since the order is what makes it work', () => {
    const steps = mountScreen().findAll('li').map(step => step.text());

    expect(steps).toStrictEqual([
      'missing_binary.steps.update_definitions',
      'missing_binary.steps.restore',
      'missing_binary.steps.exclude',
      'missing_binary.steps.reinstall',
    ]);
  });

  it('should point at Windows Security only when the report comes from Windows', () => {
    expect(mountScreen({ ...QUARANTINED_COLIBRI, onWindows: true }).text())
      .toContain('missing_binary.steps.restore_windows');
    expect(mountScreen().text()).not.toContain('missing_binary.steps.restore_windows');
  });

  it('should offer only to terminate, since the file is still gone', async () => {
    const wrapper = mountScreen();

    await wrapper.find('[data-testid=missing-binary-terminate]').trigger('click');

    expect(closeApp).toHaveBeenCalledOnce();
  });
});
