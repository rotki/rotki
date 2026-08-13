import { describe, expect, it } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
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
