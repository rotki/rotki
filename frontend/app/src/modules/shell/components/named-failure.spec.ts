import { err, ok, type Result } from 'plainfp/result';
import { describe, expect, it, vi } from 'vitest';
import { isReadonly } from 'vue';
import { useFailureSlot } from '@/modules/shell/components/named-failure';

describe('useFailureSlot', () => {
  it('should hold what report names, keeping the error itself', () => {
    const { failure, report } = useFailureSlot();
    const error = new Error('boom');

    report('Delete failed', error);

    expect(get(failure)).toEqual({ failure: error, title: 'Delete failed' });
    expect(get(failure)?.failure).toBe(error);
  });

  it('should hold nothing after clear', () => {
    const { clear, failure, report } = useFailureSlot();
    report('Delete failed', 'boom');

    clear();

    expect(get(failure)).toBeUndefined();
  });

  it('should hand consumers a failure they cannot write', () => {
    const { failure } = useFailureSlot();

    expect(isReadonly(failure)).toBe(true);
  });

  it('should keep what the action throws under the title run was given', async () => {
    const { failure, run } = useFailureSlot();
    const error = new Error('boom');

    await run('Save failed', async () => {
      throw error;
    });

    expect(get(failure)).toEqual({ failure: error, title: 'Save failed' });
  });

  it('should clear the last failure before the action runs, and leave none when it succeeds', async () => {
    const { failure, report, run } = useFailureSlot();
    report('Save failed', 'earlier');
    const seen: unknown[] = [];

    await run('Save failed', async () => {
      seen.push(get(failure));
    });

    expect(seen).toEqual([undefined]);
    expect(get(failure)).toBeUndefined();
  });

  it('should not reject when the action throws', async () => {
    const { run } = useFailureSlot();
    const action = vi.fn<() => Promise<void>>().mockRejectedValue(new Error('boom'));

    await expect(run('Save failed', action)).resolves.toBeUndefined();
    expect(action).toHaveBeenCalledOnce();
  });

  it('should keep the error of an Err the action resolves to under the title run was given', async () => {
    const { failure, run } = useFailureSlot();

    await run('Save failed', async () => err('backend refused'));

    expect(get(failure)).toEqual({ failure: 'backend refused', title: 'Save failed' });
  });

  it('should leave the slot empty when the action resolves to an Ok', async () => {
    const { failure, report, run } = useFailureSlot();
    report('Save failed', 'earlier');

    await run('Save failed', async (): Promise<Result<number, string>> => ok(1));

    expect(get(failure)).toBeUndefined();
  });
});
