import type { Ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import { z } from 'zod';
import { useForm } from '@/modules/core/form/use-form';

vi.mock('vue-i18n', () => ({
  useI18n: (): { locale: Ref<string>; t: (key: string) => string; te: (key: string) => boolean } => ({
    locale: ref(''),
    t: (key: string): string => `translated:${key}`,
    te: (key: string): boolean => key === 'amount_required',
  }),
}));

interface State {
  amount: string;
  /** Typed as optional so the spec can seed the `undefined` a cleared input writes, without a cast. */
  label: string | undefined;
}

const Schema = z.object({
  amount: z.string().min(1, 'amount_required'),
  // No message, so a missing value produces zod's own English default rather than a key.
  label: z.string(),
});

describe('useForm i18n handling', () => {
  it('should translate a schema message that is a key', () => {
    const form = useForm<State, State>({
      initial: (): State => ({ amount: '', label: '' }),
      schema: Schema,
      submit: async (): Promise<{ success: true }> => Promise.resolve({ success: true }),
      transform: (state): State => state,
    });

    form.validate();

    expect(form.errors('amount')).toStrictEqual(['translated:amount_required']);
  });

  it('should pass a zod default message through untranslated', () => {
    const form = useForm<State, State>({
      // A cleared autocomplete writes `undefined` into a field the schema types as a string.
      initial: (): State => ({ amount: '1', label: undefined }),
      schema: Schema,
      submit: async (): Promise<{ success: true }> => Promise.resolve({ success: true }),
      transform: (state): State => state,
    });

    form.validate();

    const [message] = form.errors('label');
    expect(message).not.toContain('translated:');
    expect(message).toContain('expected string');
  });
});
