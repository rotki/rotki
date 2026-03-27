import { describe, expect, it } from 'vitest';
import { useRefPropVModel } from '@/utils/model';

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
