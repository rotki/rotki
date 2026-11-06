import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ConfirmPopover from './ConfirmPopover.vue';

const QUESTION = { confirmLabel: 'Delete', message: 'Delete this backup?', tone: 'error' } as const;

function createWrapper(): VueWrapper<InstanceType<typeof ConfirmPopover>> {
  return mount(ConfirmPopover, {
    attachTo: document.body,
    props: { question: QUESTION },
    slots: {
      activator: `<template #activator="{ attrs }">
        <button data-testid="trigger" v-bind="attrs">Delete</button>
      </template>`,
    },
  });
}

function byTestId(id: string): HTMLElement | null {
  return document.body.querySelector<HTMLElement>(`[data-testid=${id}]`);
}

async function openQuestion(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('[data-testid=trigger]').trigger('click');
  await vi.waitFor(() => expect(byTestId('inline-confirm-cancel')).not.toBeNull());
  await flushPromises();
}

describe('confirmPopover', () => {
  it('should leave focus on cancel once the question has opened, so enter cannot delete', async () => {
    const wrapper = createWrapper();

    await openQuestion(wrapper);

    expect(document.activeElement).toBe(byTestId('inline-confirm-cancel'));
  });

  it('should confirm once on accept and hand focus back to the trigger', async () => {
    const wrapper = createWrapper();
    await openQuestion(wrapper);

    byTestId('inline-confirm-accept')?.click();
    await flushPromises();

    expect(wrapper.emitted('confirm')).toHaveLength(1);
    expect(document.activeElement).toBe(byTestId('trigger'));
  });

  it('should not confirm on cancel, and hand focus back to the trigger', async () => {
    const wrapper = createWrapper();
    await openQuestion(wrapper);

    byTestId('inline-confirm-cancel')?.click();
    await flushPromises();

    expect(wrapper.emitted('confirm')).toBeUndefined();
    expect(byTestId('inline-confirm')).toBeNull();
    expect(document.activeElement).toBe(byTestId('trigger'));
  });
});
