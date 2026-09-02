import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import ResolveManuallyDialog from '@/modules/history/data-issues/components/ResolveManuallyDialog.vue';

async function mountDialog(open = true): Promise<VueWrapper<InstanceType<typeof ResolveManuallyDialog>>> {
  const wrapper = mount(ResolveManuallyDialog, {
    attachTo: document.body,
    props: {
      modelValue: open,
    },
    provide: libraryDefaults,
  });
  await flushPromises();
  await nextTick();
  return wrapper;
}

function queryNote(): HTMLTextAreaElement {
  const note = document.body.querySelector<HTMLTextAreaElement>('[data-testid="data-issue-resolve-note"] textarea');
  if (!note)
    throw new Error('resolve note textarea not in DOM');
  return note;
}

async function setNote(value: string): Promise<void> {
  const note = queryNote();
  note.value = value;
  note.dispatchEvent(new Event('input'));
  await nextTick();
}

function clickConfirm(): void {
  const confirm = document.body.querySelector<HTMLButtonElement>('[data-testid="data-issue-resolve-confirm"]');
  if (!confirm)
    throw new Error('resolve confirm button not in DOM');
  confirm.click();
}

describe('resolveManuallyDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof ResolveManuallyDialog>>;

  beforeEach(async () => {
    wrapper = await mountDialog();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('should emit the trimmed note on confirm', async () => {
    await setNote('  fixed externally  ');

    clickConfirm();

    expect(wrapper.emitted('confirm')?.[0]).toStrictEqual(['fixed externally']);
  });

  it('should emit undefined when the note is empty or whitespace only', async () => {
    await setNote('   ');

    clickConfirm();

    expect(wrapper.emitted('confirm')?.[0]).toStrictEqual([undefined]);
  });

  it('should reset the note each time the dialog is reopened', async () => {
    await setNote('stale note');
    await wrapper.setProps({ modelValue: false });
    await wrapper.setProps({ modelValue: true });
    await flushPromises();
    await nextTick();

    clickConfirm();

    expect(wrapper.emitted('confirm')?.[0]).toStrictEqual([undefined]);
  });
});
