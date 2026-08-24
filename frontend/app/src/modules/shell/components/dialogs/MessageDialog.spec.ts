import { resetOverlayStack, useOverlayStack } from '@rotki/ui-library';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import MessageDialog from '@/modules/shell/components/dialogs/MessageDialog.vue';

function createWrapper(): VueWrapper<InstanceType<typeof MessageDialog>> {
  return mount(MessageDialog, {
    attachTo: document.body,
    props: { message: { description: 'description', success: false, title: 'Auto Match Failed' } },
  });
}

describe('modules/shell/components/dialogs/MessageDialog', () => {
  beforeEach(() => {
    resetOverlayStack();
  });

  it('should dismiss the message when dismissed from the overlay stack, as the back gesture does', () => {
    const wrapper = createWrapper();

    expect(useOverlayStack().dismissTop()).toBe(true);
    expect(wrapper.emitted('dismiss')).toHaveLength(1);
  });

  it('should leave the overlay stack once unmounted', () => {
    createWrapper().unmount();

    expect(useOverlayStack().dismissTop()).toBe(false);
  });
});
