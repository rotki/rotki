import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, nextTick, ref } from 'vue';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const mockWrite = vi.fn(async (): Promise<{ success: boolean; message?: string }> => ({ success: true }));
const mockSource = ref<number>(25);

vi.mock('@/modules/settings/settings-writer', () => ({
  useSettingsWriter: vi.fn((): Record<string, unknown> => ({
    write: mockWrite,
  })),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => mockSource),
}));

describe('useSettingModel', () => {
  let scope: EffectScope;

  beforeEach(() => {
    vi.clearAllMocks();
    set(mockSource, 25);
    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
  });

  function createModel(options?: { debounce?: number }): ReturnType<typeof useSettingModel<'itemsPerPage'>> {
    return scope.run(() => useSettingModel('itemsPerPage', options))!;
  }

  it('should initialize the model from the current setting value', () => {
    const { model } = createModel();
    expect(get(model)).toBe(25);
  });

  it('should persist through the writer when the model changes', async () => {
    const { model } = createModel();
    set(model, 50);
    await nextTick();
    await flushPromises();
    expect(mockWrite).toHaveBeenCalledWith('itemsPerPage', 50);
  });

  it('should expose success after a successful write', async () => {
    const { error, model, pending, success } = createModel();
    set(model, 50);
    await nextTick();
    await flushPromises();
    expect(get(success)).toBe(true);
    expect(get(error)).toBe('');
    expect(get(pending)).toBe(false);
  });

  it('should expose the error message on a failed write', async () => {
    mockWrite.mockResolvedValueOnce({ message: 'bad value', success: false });
    const { error, model, success } = createModel();
    set(model, 50);
    await nextTick();
    await flushPromises();
    expect(get(error)).toBe('bad value');
    expect(get(success)).toBe(false);
  });

  it('should reflect external setting changes into the model without persisting', async () => {
    const { model } = createModel();
    set(mockSource, 99);
    await nextTick();
    expect(get(model)).toBe(99);
    await flushPromises();
    expect(mockWrite).not.toHaveBeenCalled();
  });

  it('should not persist when set to the current value', async () => {
    const { model } = createModel();
    set(model, 25);
    await nextTick();
    await flushPromises();
    expect(mockWrite).not.toHaveBeenCalled();
  });

  it('should debounce persistence when configured', async () => {
    vi.useFakeTimers();
    try {
      const { model } = createModel({ debounce: 500 });
      set(model, 50);
      await nextTick();
      await vi.advanceTimersByTimeAsync(400);
      expect(mockWrite).not.toHaveBeenCalled();
      await vi.advanceTimersByTimeAsync(200);
      expect(mockWrite).toHaveBeenCalledWith('itemsPerPage', 50);
    }
    finally {
      vi.useRealTimers();
    }
  });

  it('should not persist a transient edit reverted to the source within the debounce window', async () => {
    vi.useFakeTimers();
    try {
      const { model } = createModel({ debounce: 500 });
      set(model, 50);
      await nextTick();
      await vi.advanceTimersByTimeAsync(300);
      // revert to the persisted value before the pending debounced write fires
      set(model, 25);
      await nextTick();
      await vi.advanceTimersByTimeAsync(500);
      expect(mockWrite).not.toHaveBeenCalled();
    }
    finally {
      vi.useRealTimers();
    }
  });
});
