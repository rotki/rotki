import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { startPromise } from '@shared/utils';
import { describe, expect, it } from 'vitest';
import { customRef, nextTick, type Ref, ref } from 'vue';
import { z } from 'zod';
import { useModelForm } from '@/modules/core/form/use-model-form';

interface PriceState {
  fromAsset: string;
  price: string;
  sourceType: string;
  /** Nested on purpose: a copied array is a new reference every time, unlike a copied string. */
  tags: string[];
}

const PriceSchema = z.object({
  fromAsset: z.string().min(1, 'from_required'),
  price: z.string().min(1, 'price_required'),
  sourceType: z.string(),
  tags: z.array(z.string()),
});

function baseModel(): PriceState {
  return { fromAsset: 'ETH', price: '2500', sourceType: 'manual', tags: ['manual'] };
}

describe('useModelForm', () => {
  it('should seed the state from the model', () => {
    const model = ref<PriceState>(baseModel());
    const form = useModelForm<PriceState>({ model, schema: PriceSchema });

    expect(form.state.price).toBe('2500');
  });

  it('should write an edit back into the model', async () => {
    const model = ref<PriceState>(baseModel());
    const form = useModelForm<PriceState>({ model, schema: PriceSchema });

    form.state.price = '3000';
    await nextTick();

    expect(get(model).price).toBe('3000');
  });

  it('should pull an edit made outside the form back in', async () => {
    const model = ref<PriceState>(baseModel());
    const form = useModelForm<PriceState>({ model, schema: PriceSchema });

    set(model, { ...baseModel(), price: '4000' });
    await nextTick();

    expect(form.state.price).toBe('4000');
  });

  // Pins convergence, not the equality guard: removing the guard leaves this green, because the
  // copy is shallow and re-assigning the same nested reference is not a reactive change. Written
  // with a nested value on purpose, since that is the only shape that could echo at all.
  it('should settle rather than echo between the two directions', async () => {
    const model = ref<PriceState>(baseModel());
    const form = useModelForm<PriceState>({ model, schema: PriceSchema });

    let writes = 0;
    watch(model, () => {
      writes += 1;
    }, { deep: true });

    form.state.price = '3000';
    await nextTick();
    await nextTick();
    await nextTick();

    expect(writes).toBe(1);
    expect(form.state.price).toBe('3000');
    expect(get(model).price).toBe('3000');
  });

  describe('stateUpdated', () => {
    function createWithFlag(flag: Ref<boolean>): ReturnType<typeof useModelForm<PriceState>> {
      return useModelForm<PriceState>({ model: ref<PriceState>(baseModel()), schema: PriceSchema, stateUpdated: flag });
    }

    it('should arm the flag once a field is edited', async () => {
      const stateUpdated = ref<boolean>(false);
      const form = createWithFlag(stateUpdated);

      form.state.price = '3000';
      await nextTick();

      expect(get(stateUpdated)).toBe(true);
    });

    it('should disarm the flag when the edit is reverted', async () => {
      const stateUpdated = ref<boolean>(false);
      const form = createWithFlag(stateUpdated);

      form.state.price = '3000';
      await nextTick();
      form.state.price = '2500';
      await nextTick();

      expect(get(stateUpdated)).toBe(false);
    });

    // A dialog holds its prompt-on-close flag in its own ref, which outlives the form it passes it
    // to. Reopening it after an abandoned edit used to rely on the form disarming the flag as it
    // unmounted; the sync being immediate covers it from the other end.
    it('should disarm a flag left armed by a previous edit', () => {
      const stateUpdated = ref<boolean>(true);
      createWithFlag(stateUpdated);

      expect(get(stateUpdated)).toBe(false);
    });
  });

  describe('seed', () => {
    it('should open on the seeded value', () => {
      const model = ref<PriceState>(baseModel());
      const form = useModelForm<PriceState>({
        model,
        schema: PriceSchema,
        seed: state => ({ ...state, sourceType: 'oracle' }),
      });

      expect(form.state.sourceType).toBe('oracle');
    });

    it('should not count the seeding as an edit', async () => {
      const stateUpdated = ref<boolean>(false);
      const form = useModelForm<PriceState>({
        model: ref<PriceState>(baseModel()),
        schema: PriceSchema,
        seed: state => ({ ...state, sourceType: 'oracle' }),
        stateUpdated,
      });
      await nextTick();

      expect(get(form.dirty)).toBe(false);
      expect(get(stateUpdated)).toBe(false);
    });

    it('should put the seeded value in the model the dialog saves', () => {
      const model = ref<PriceState>(baseModel());
      useModelForm<PriceState>({
        model,
        schema: PriceSchema,
        seed: state => ({ ...state, sourceType: 'oracle' }),
      });

      expect(get(model).sourceType).toBe('oracle');
    });

    /*
     * A `defineModel` ref reads back the value from before the write until the parent catches up, so
     * the model still reports the pre-seed payload right after the form seeds it. Asserted on the
     * spot, with no tick in between: let the ref catch up first and the state converges either way,
     * which is what made an earlier version of this test unable to fail.
     */
    it('should not let a stale model read undo the seeding', () => {
      const inner = ref<PriceState>(baseModel());
      const lagging = customRef<PriceState>((track, trigger) => ({
        get: (): PriceState => {
          track();
          return get(inner);
        },
        set: (value): void => {
          startPromise(nextTick().then(() => {
            set(inner, value);
            trigger();
          }));
        },
      }));

      const form = useModelForm<PriceState>({
        model: lagging,
        schema: PriceSchema,
        seed: state => ({ ...state, sourceType: 'oracle' }),
      });

      expect(form.state.sourceType).toBe('oracle');
      expect(get(form.dirty)).toBe(false);
    });

    it('should still edit normally after seeding', async () => {
      const model = ref<PriceState>(baseModel());
      const form = useModelForm<PriceState>({
        model,
        schema: PriceSchema,
        seed: state => ({ ...state, sourceType: 'oracle' }),
      });

      form.state.price = '3000';
      await nextTick();

      expect(get(model).price).toBe('3000');
      expect(get(form.dirty)).toBe(true);
    });
  });

  describe('serverErrors', () => {
    it('should surface errors the dialog is already holding when the form mounts', () => {
      const form = useModelForm<PriceState>({
        model: ref<PriceState>(baseModel()),
        schema: PriceSchema,
        serverErrors: ref({ price: 'already known' }),
      });

      expect(form.errors('price')).toEqual(['already known']);
    });

    it('should surface errors reported after a failed save', async () => {
      const serverErrors = ref<ValidationErrors>({});
      const form = useModelForm<PriceState>({ model: ref<PriceState>(baseModel()), schema: PriceSchema, serverErrors });

      set(serverErrors, { price: ['too high', 'and wrong'] });
      await nextTick();

      expect(form.errors('price')).toEqual(['too high', 'and wrong']);
    });

    it('should drop a server error once the field it names is edited', async () => {
      const serverErrors = ref<ValidationErrors>({ price: 'already known' });
      const form = useModelForm<PriceState>({ model: ref<PriceState>(baseModel()), schema: PriceSchema, serverErrors });

      form.state.price = '3000';
      await nextTick();

      expect(form.errors('price')).toEqual([]);
    });
  });

  it('should keep a transient key out of the dirty comparison', async () => {
    const model = ref<PriceState>(baseModel());
    const form = useModelForm<PriceState>({ model, schema: PriceSchema, transientKeys: ['sourceType'] });

    form.state.sourceType = 'cryptocompare';
    await nextTick();

    expect(get(form.dirty)).toBe(false);

    form.state.price = '3000';
    await nextTick();

    expect(get(form.dirty)).toBe(true);
  });
});
