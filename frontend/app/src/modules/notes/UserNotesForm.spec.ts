import type { UserNoteDraft } from '@/modules/core/common/notes';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import UserNotesForm from '@/modules/notes/UserNotesForm.vue';
import '@test/i18n';

describe('userNotesForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof UserNotesForm>>;

  const baseModel = (): UserNoteDraft => ({
    content: 'a note',
    title: 'a title',
  });

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(modelValue: UserNoteDraft = baseModel()): VueWrapper<InstanceType<typeof UserNotesForm>> {
    return mount(UserNotesForm, { props: { modelValue } });
  }

  function contentMessages(): string[] {
    const value: unknown = wrapper.findComponent({ name: 'RuiTextArea' }).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  /** `auto-grow` renders a second, mirror textarea, so the model is driven through the component. */
  async function editContent(value: string): Promise<void> {
    wrapper.findComponent({ name: 'RuiTextArea' }).vm.$emit('update:modelValue', value);
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should pass validation when the content is filled', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should fail validation when the content is empty', async () => {
    wrapper = createWrapper({ ...baseModel(), content: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should treat whitespace-only content as empty', async () => {
    wrapper = createWrapper({ ...baseModel(), content: '   ' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should not require a title, its placeholder rule object being no rule', async () => {
    wrapper = createWrapper({ content: 'a note', title: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should show an untitled note as an empty field', async () => {
    wrapper = createWrapper({ content: 'a note', title: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('input').element.value).toBe('');
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper({ content: '', title: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(contentMessages()).toEqual([]);
  });

  it('should reveal the content message once validate runs', async () => {
    wrapper = createWrapper({ content: '', title: '' });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(contentMessages()).toEqual(['notes_menu.rules.content.non_empty']);
  });

  it('should show the content message once the field is emptied', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await editContent('');

    expect(contentMessages()).toEqual(['notes_menu.rules.content.non_empty']);
  });

  it('should write an edit back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await editContent('edited');

    const updates = wrapper.emitted<[UserNoteDraft]>('update:modelValue');
    expect(updates).toBeTruthy();
    const last = updates!.at(-1)![0];
    expect(last.content).toBe('edited');
    expect(last.title).toBe('a title');
  });

  it('should write a cleared title back as an empty string', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('input').setValue('');
    await vi.advanceTimersToNextTimerAsync();

    const updates = wrapper.emitted<[UserNoteDraft]>('update:modelValue');
    expect(updates!.at(-1)![0].title).toBe('');
  });

  it('should flag stateUpdated when only the title is edited, which no rule validates', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    await wrapper.find('input').setValue('a new title');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should not flag stateUpdated before anything is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).not.toEqual([true]);
  });
});
