import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { FormApi } from '@/modules/core/form/use-form';
import { startPromise } from '@shared/utils';
import { describe, expect, it } from 'vitest';
import { customRef, nextTick, type Ref, ref, type UnwrapNestedRefs } from 'vue';
import { z } from 'zod';
import { useMappedModelForm, useModelForm } from '@/modules/core/form/use-model-form';

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

    it('should disarm, on creation, a flag left armed by a previous edit', () => {
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

  describe('mapped state', () => {
    /** The payload admits null where the input needs a string, which is the usual reason to map. */
    interface PriceModel {
      fromAsset: string;
      price: string | null;
      sourceType: string;
      tags: string[] | null;
    }

    interface MappedOverrides {
      model?: Ref<PriceModel>;
      stateUpdated?: Ref<boolean>;
    }

    function baseMapped(): PriceModel {
      return { fromAsset: 'ETH', price: null, sourceType: 'manual', tags: null };
    }

    function createMapped(overrides: MappedOverrides = {}): FormApi<PriceState, UnwrapNestedRefs<PriceState>> {
      return useMappedModelForm<PriceModel, PriceState>({
        model: overrides.model ?? ref<PriceModel>(baseMapped()),
        schema: PriceSchema,
        stateUpdated: overrides.stateUpdated,
        toModel: (state, model): PriceModel => ({ ...model, ...state }),
        // A new array every call on purpose: the mirroring has to notice that it holds the same
        // values rather than that it is the same reference.
        toState: (model): PriceState => ({
          fromAsset: model.fromAsset,
          price: model.price ?? '',
          sourceType: model.sourceType,
          tags: [...(model.tags ?? [])],
        }),
      });
    }

    it('should open on the mapped state rather than the payload', () => {
      const form = createMapped();

      expect(form.state.price).toBe('');
      expect(form.state.tags).toEqual([]);
    });

    it('should write an edit back through the payload mapper', async () => {
      const model = ref<PriceModel>(baseMapped());
      const form = createMapped({ model });

      form.state.price = '3000';
      await nextTick();

      expect(get(model).price).toBe('3000');
    });

    it('should leave the payload fields the state does not carry alone', async () => {
      const model = ref<PriceModel>({ ...baseMapped(), fromAsset: 'BTC' });
      const form = createMapped({ model });

      form.state.price = '3000';
      await nextTick();

      // `toModel` is handed the payload precisely so a form editing part of one can fold over it.
      expect(get(model).fromAsset).toBe('BTC');
    });

    it('should map an edit made outside the form on the way in', async () => {
      const model = ref<PriceModel>(baseMapped());
      const form = createMapped({ model });

      set(model, { ...baseMapped(), price: null, sourceType: 'oracle' });
      await nextTick();

      expect(form.state.sourceType).toBe('oracle');
      expect(form.state.price).toBe('');
    });

    /*
     * Unlike the unmapped case above, this one does pin the equality guard rather than merely
     * documenting it. `toState` answers with a new array every call, so without the comparison the
     * mirroring would assign a fresh reference each pass, the write-back would answer with a fresh
     * payload, and the two would trade writes until the test timed out.
     */
    it('should settle even though the mapper answers with a new object each time', async () => {
      const model = ref<PriceModel>({ ...baseMapped(), tags: ['manual'] });
      const form = createMapped({ model });

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
      expect(form.state.tags).toEqual(['manual']);
    });

    it('should not read the mapping itself as an edit', async () => {
      const stateUpdated = ref<boolean>(false);
      const form = createMapped({ stateUpdated });
      await nextTick();

      // Opening on '' where the payload holds null is the mapper doing its job, not the user typing.
      expect(get(form.dirty)).toBe(false);
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
