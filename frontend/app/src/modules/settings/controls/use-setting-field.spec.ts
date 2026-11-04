import type { Ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import { z } from 'zod';
import { SETTING_FIELD } from '@/modules/settings/controls/setting-field-schemas';
import { useSettingField } from '@/modules/settings/controls/use-setting-field';

const schema = z.object({ [SETTING_FIELD]: z.string().regex(/^\d+$/) });

function create(initial = 5): { model: Ref<number>; onEdit: () => void } & ReturnType<typeof useSettingField> {
  const model = ref<number>(initial);
  const onEdit = vi.fn<() => void>();
  const field = useSettingField({ fromField: Number, model, onEdit, schema, toField: String });
  return { model, onEdit, ...field };
}

describe('useSettingField', () => {
  it('should start the field from the stored value', () => {
    const { form } = create(7);

    expect(form.state.value).toBe('7');
  });

  it('should write a valid entry into the setting', async () => {
    const { model, onInput, onEdit } = create();

    await onInput('42');

    expect(onEdit).toHaveBeenCalledOnce();
    expect(get(model)).toBe(42);
  });

  it('should keep an invalid entry out of the setting', async () => {
    const { form, model, onInput } = create();

    await onInput('4x');

    expect(form.state.value).toBe('4x');
    expect(get(model)).toBe(5);
  });

  it('should mirror a change made elsewhere into the field', async () => {
    const { form, model } = create();

    set(model, 9);
    await nextTick();

    expect(form.state.value).toBe('9');
  });
});
