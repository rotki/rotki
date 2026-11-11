import { describe, expect, it, vi } from 'vitest';
import { shallowRef } from 'vue';
import { useStepCheck } from '@/modules/auth/create-account/use-step-check';

interface FakeForm {
  validate: () => Promise<boolean>;
  errorCount: number;
}

function fakeForm(valid: boolean, errorCount: number): FakeForm {
  return { errorCount, validate: vi.fn<() => Promise<boolean>>().mockResolvedValue(valid) };
}

describe('useStepCheck', () => {
  it('should count nothing before the user tries to move on, even with errors pending', () => {
    const { issueCount } = useStepCheck(shallowRef<FakeForm>(fakeForm(false, 3)));

    expect(get(issueCount)).toBe(0);
  });

  it('should count the form\'s errors once the user has tried to move on', async () => {
    const { issueCount, validate } = useStepCheck(shallowRef<FakeForm>(fakeForm(false, 3)));

    await expect(validate()).resolves.toBe(false);

    expect(get(issueCount)).toBe(3);
  });

  it('should follow the count as the user fixes fields', async () => {
    const form = shallowRef<FakeForm>(fakeForm(false, 3));
    const { issueCount, validate } = useStepCheck(form);
    await validate();

    set(form, fakeForm(false, 1));

    expect(get(issueCount)).toBe(1);
  });

  it('should let the step go when the form is valid', async () => {
    const { validate } = useStepCheck(shallowRef<FakeForm>(fakeForm(true, 0)));

    await expect(validate()).resolves.toBe(true);
  });

  /** A collapsed optional section renders no form, and what was typed in it is not sent. */
  it('should let the step go when there is no form to check', async () => {
    const { issueCount, validate } = useStepCheck(shallowRef<FakeForm | null>(null));

    await expect(validate()).resolves.toBe(true);
    expect(get(issueCount)).toBe(0);
  });
});
