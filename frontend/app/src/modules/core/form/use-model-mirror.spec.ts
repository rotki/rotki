import { describe, expect, it } from 'vitest';
import { nextTick, reactive, type Ref, ref } from 'vue';
import { useModelMirror } from '@/modules/core/form/use-model-mirror';

/** The payload, as the api admits it: the optional half can be absent. */
interface Rule {
  name: string;
  linkedSetting?: string;
  tags?: string[];
}

/** The same rule as the inputs need it: a string to type into, and the link as its own flag. */
interface RuleState {
  name: string;
  linked: boolean;
  linkedSetting: string;
  tags: string[];
}

function toState(rule: Rule): RuleState {
  return {
    linked: Boolean(rule.linkedSetting),
    linkedSetting: rule.linkedSetting ?? '',
    name: rule.name,
    // A new array every call, so the mirroring has to compare values rather than references.
    tags: [...(rule.tags ?? [])],
  };
}

function toModel(state: RuleState, rule: Rule): Rule {
  return {
    ...rule,
    linkedSetting: state.linked ? state.linkedSetting : undefined,
    name: state.name,
    tags: state.tags,
  };
}

interface Mirrored {
  model: Ref<Rule>;
  state: RuleState;
}

function mirror(initial: Rule, seed?: (state: RuleState) => RuleState): Mirrored {
  const model = ref<Rule>(initial);
  const opening = toState(get(model));
  const state = reactive<RuleState>(seed ? seed(opening) : opening);

  useModelMirror<Rule, RuleState>({
    model,
    seeded: Boolean(seed),
    state,
    toModel,
    toState,
  });

  return { model, state };
}

describe('useModelMirror', () => {
  it('should open on the mapped state rather than the payload', () => {
    const { state } = mirror({ name: 'gas' });

    expect(state.linked).toBe(false);
    expect(state.linkedSetting).toBe('');
    expect(state.tags).toEqual([]);
  });

  it('should read an absent field as its mapped presence flag', () => {
    const { state } = mirror({ linkedSetting: 'includeGasCosts', name: 'gas' });

    expect(state.linked).toBe(true);
  });

  it('should write an edit back through the payload mapper', async () => {
    const { model, state } = mirror({ name: 'gas' });

    state.linked = true;
    state.linkedSetting = 'includeGasCosts';
    await nextTick();

    expect(get(model).linkedSetting).toBe('includeGasCosts');
  });

  it('should drop the field again when its flag is turned off', async () => {
    const { model, state } = mirror({ linkedSetting: 'includeGasCosts', name: 'gas' });

    state.linked = false;
    await nextTick();

    // Absent, not empty: the api reads an absent field as "this rule has no link".
    expect(get(model).linkedSetting).toBeUndefined();
  });

  it('should leave the payload fields the state does not carry alone', async () => {
    const model = ref<Rule>({ name: 'gas' });
    const state = reactive<RuleState>(toState(get(model)));
    useModelMirror<Rule, RuleState>({
      model,
      state,
      toModel: (next, rule): Rule => ({ ...rule, name: next.name }),
      toState,
    });

    set(model, { ...get(model), linkedSetting: 'includeGasCosts' });
    await nextTick();
    state.name = 'renamed';
    await nextTick();

    expect(get(model).linkedSetting).toBe('includeGasCosts');
  });

  it('should map an edit made outside on the way in', async () => {
    const { model, state } = mirror({ name: 'gas' });

    set(model, { linkedSetting: 'includeGasCosts', name: 'gas' });
    await nextTick();

    expect(state.linked).toBe(true);
    expect(state.linkedSetting).toBe('includeGasCosts');
  });

  /*
   * The equality guard is what makes this terminate rather than being defensive: `toState` answers
   * with a new array every call, so without the comparison the mirroring would assign a fresh
   * reference each pass, the write-back would answer with a fresh payload, and the two would trade
   * writes until Vue's recursion limit.
   */
  it('should settle even though the mapper answers with a new object each time', async () => {
    const { model, state } = mirror({ name: 'gas', tags: ['manual'] });

    let writes = 0;
    watch(model, () => {
      writes += 1;
    }, { deep: true });

    state.name = 'renamed';
    await nextTick();
    await nextTick();
    await nextTick();

    expect(writes).toBe(1);
    expect(get(model).name).toBe('renamed');
    expect(state.tags).toEqual(['manual']);
  });

  describe('seeded', () => {
    it('should put the seeded value in the payload the parent saves', () => {
      const { model } = mirror({ name: '' }, state => ({ ...state, name: 'suggested' }));

      expect(get(model).name).toBe('suggested');
    });

    it('should not let the payload undo the seeding', async () => {
      const { model, state } = mirror({ name: '' }, next => ({ ...next, name: 'suggested' }));
      await nextTick();

      // The immediate pull is skipped precisely so the older payload does not win this race.
      expect(state.name).toBe('suggested');
      expect(get(model).name).toBe('suggested');
    });
  });
});
