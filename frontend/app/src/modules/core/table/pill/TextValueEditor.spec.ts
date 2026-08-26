import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TextValueEditor from '@/modules/core/table/pill/TextValueEditor.vue';

const notesField: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'filter' },
  freeText: true,
  key: 'notesSubstring',
  label: 'Notes',
  multiple: false,
  operators: ['is'],
  valueType: 'enum',
};

const txField: FieldDef = {
  ...notesField,
  key: 'txRefs',
  label: 'Tx hash',
  multiple: true,
};

function createWrapper(field: FieldDef, filter: ActiveFilter): VueWrapper<InstanceType<typeof TextValueEditor>> {
  return mount(TextValueEditor, {
    // The address preview scrambles through the settings repo.
    global: { plugins: [createCustomPinia()] },
    props: { field, filter },
  });
}

async function typeAndEnter(
  wrapper: VueWrapper<InstanceType<typeof TextValueEditor>>,
  value: string,
): Promise<void> {
  const input = wrapper.find('[data-testid=text-input] input');
  await input.setValue(value);
  await input.trigger('keydown.enter');
}

describe('textValueEditor', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // Regression: a single-value field commits through a 300ms debounce, so pressing Enter before
  // it elapsed closed the editor with the commit still pending and silently dropped the value.
  it('should commit a single value on enter without waiting for the debounce', async () => {
    const wrapper = createWrapper(notesField, { fieldKey: 'notesSubstring', op: 'is', values: [] });

    await typeAndEnter(wrapper, 'pillfilter gamma');

    const updates = wrapper.emitted('update');
    expect(updates).toHaveLength(1);
    expect(updates?.[0]).toEqual([{ fieldKey: 'notesSubstring', op: 'is', values: ['pillfilter gamma'] }]);
    expect(wrapper.emitted('close')).toHaveLength(1);
  });

  it('should still commit a single value through the debounce when enter is not pressed', async () => {
    const wrapper = createWrapper(notesField, { fieldKey: 'notesSubstring', op: 'is', values: [] });

    await wrapper.find('[data-testid=text-input] input').setValue('pillfilter delta');
    expect(wrapper.emitted('update')).toBeUndefined();

    await vi.advanceTimersByTimeAsync(300);

    expect(wrapper.emitted('update')?.[0]).toEqual([
      { fieldKey: 'notesSubstring', op: 'is', values: ['pillfilter delta'] },
    ]);
    expect(wrapper.emitted('close')).toBeUndefined();
  });

  it('should bank a token and stay open for a multi field', async () => {
    const wrapper = createWrapper(txField, { fieldKey: 'txRefs', op: 'is', values: ['0xaa'] });

    await typeAndEnter(wrapper, '0xbb');

    expect(wrapper.emitted('update')?.[0]).toEqual([
      { fieldKey: 'txRefs', op: 'is', values: ['0xaa', '0xbb'] },
    ]);
    expect(wrapper.emitted('close')).toBeUndefined();
  });

  it('should commit a pending single value when the editor closes', async () => {
    const wrapper = createWrapper(notesField, { fieldKey: 'notesSubstring', op: 'is', values: [] });

    await wrapper.find('[data-testid=text-input] input').setValue('pillfilter zeta');
    expect(wrapper.emitted('update')).toBeUndefined();

    wrapper.unmount();

    expect(wrapper.emitted('update')?.[0]).toEqual([
      { fieldKey: 'notesSubstring', op: 'is', values: ['pillfilter zeta'] },
    ]);
  });

  it('should not re-commit on close when nothing changed', async () => {
    const wrapper = createWrapper(notesField, {
      fieldKey: 'notesSubstring',
      op: 'is',
      values: ['pillfilter zeta'],
    });

    wrapper.unmount();

    expect(wrapper.emitted('update')).toBeUndefined();
  });

  it('should not commit a value its field rejects', async () => {
    const validated: FieldDef = { ...notesField, validate: (value: string): boolean => value.startsWith('0x') };
    const wrapper = createWrapper(validated, { fieldKey: 'notesSubstring', op: 'is', values: [] });

    await typeAndEnter(wrapper, 'nope');

    expect(wrapper.emitted('update')).toBeUndefined();
    expect(wrapper.emitted('close')).toBeUndefined();
  });
  // The single-value field's input IS its committed value, so once the debounce banks what was
  // typed it would otherwise be flagged as a duplicate of itself: the notes filter said "Already
  // added" about the text in its own box and then refused to commit any edit of it.
  it('should not call a single-value field a duplicate of itself', async () => {
    const wrapper = createWrapper(notesField, { fieldKey: 'notesSubstring', op: 'is', values: ['swap'] });

    await wrapper.get('[data-testid=text-input] input').setValue('swap');

    expect(wrapper.text()).not.toContain('duplicate_value');
  });
});
