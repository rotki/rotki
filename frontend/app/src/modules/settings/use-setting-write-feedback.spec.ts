import type { Ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { resolveSettingMessage, useSettingWriteFeedback } from '@/modules/settings/use-setting-write-feedback';

describe('useSettingWriteFeedback', () => {
  let model: Ref<string[]>;
  let success: Ref<boolean>;
  let error: Ref<string>;

  function create(message: () => string = () => 'saved the order'): ReturnType<typeof useSettingWriteFeedback> {
    return useSettingWriteFeedback({ error, model, success }, message);
  }

  beforeEach(() => {
    model = ref<string[]>([]);
    success = ref<boolean>(false);
    error = ref<string>('');
  });

  it('should start with no message', () => {
    const feedback = create();

    expect(get(feedback.success)).toBe('');
    expect(get(feedback.error)).toBe('');
  });

  it('should report the success message once the write lands', async () => {
    const feedback = create();

    set(success, true);
    await nextTick();

    expect(get(feedback.success)).toContain('saved the order');
  });

  it('should read the success message at fire time', async () => {
    let chain = 'optimism';
    const feedback = create(() => `saved ${chain}`);

    chain = 'base';
    set(success, true);
    await nextTick();

    expect(get(feedback.success)).toContain('saved base');
  });

  it('should report the write error', async () => {
    const feedback = create();

    set(error, 'the backend said no');
    await nextTick();

    expect(get(feedback.error)).toContain('the backend said no');
  });

  it('should clear both messages when the draft changes again', async () => {
    const feedback = create();

    set(success, true);
    set(error, 'the backend said no');
    await nextTick();

    set(model, ['etherscan']);
    await nextTick();

    expect(get(feedback.success)).toBe('');
    expect(get(feedback.error)).toBe('');
  });

  it('should ignore a write flag that resets to its idle value', async () => {
    const feedback = create();

    set(success, true);
    await nextTick();
    set(success, false);
    set(error, '');
    await nextTick();

    expect(get(feedback.success)).toContain('saved the order');
    expect(get(feedback.error)).toBe('');
  });

  it('should prefix the write error when a prefix is given', async () => {
    const feedback = useSettingWriteFeedback({ error, model, success }, () => '', { errorPrefix: () => 'could not save' });

    set(error, 'the backend said no');
    await nextTick();

    expect(get(feedback.error)).toContain('could not save: the backend said no');
  });

  it('should announce the save only after it lands', async () => {
    const onSaved = vi.fn<() => void>();
    useSettingWriteFeedback({ error, model, success }, () => '', { onSaved });

    set(error, 'the backend said no');
    await nextTick();
    expect(onSaved).not.toHaveBeenCalled();

    set(success, true);
    await nextTick();
    expect(onSaved).toHaveBeenCalledOnce();
  });
});

describe('resolveSettingMessage', () => {
  it('should return static text as is', () => {
    expect(resolveSettingMessage('saved', 3)).toBe('saved');
  });

  it('should hand the value to a callback message', () => {
    expect(resolveSettingMessage((value: number) => `saved ${value}`, 3)).toBe('saved 3');
  });
});
