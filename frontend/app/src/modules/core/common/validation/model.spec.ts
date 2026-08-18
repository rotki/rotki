import { describe, expect, it } from 'vitest';
import { useRefPropVModel } from '@/modules/core/common/validation/model';

describe('model-utils', () => {
  it('should properly map computed property to parent ref', () => {
    const objRef = ref({
      title: 'title',
      value: 'value',
    });

    const prop = useRefPropVModel(objRef, 'value');
    expect(get(objRef).value).toBe('value');
    expect(get(prop)).toBe('value');
    set(prop, 'newValue');
    expect(get(prop)).toBe('newValue');
    expect(get(objRef).value).toBe('newValue');
  });
});

describe('useRefPropVModel transform', () => {
  it('should apply the transform when the value is truthy', () => {
    const obj = ref<{ name: string }>({ name: 'alice' });
    const model = useRefPropVModel(obj, 'name', { transform: value => value.toUpperCase() });
    set(model, 'bob');
    expect(get(obj).name).toBe('BOB');
  });

  it('should skip the transform for a falsy value', () => {
    const obj = ref<{ name: string }>({ name: 'alice' });
    const model = useRefPropVModel(obj, 'name', { transform: value => value.toUpperCase() });
    set(model, '');
    expect(get(obj).name).toBe('');
  });
});
