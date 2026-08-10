import type { FieldDef, FilterState } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import { pruneInadmissible } from '@/modules/core/table/pill/core/admissibility';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';

/** Subtypes stand in for the history rule: what each event type admits. */
const SUBTYPES: Record<string, string[]> = {
  receive: ['airdrop', 'reward'],
  spend: ['fee', 'return_wrapped'],
};

function fields(admits?: FieldDef['admits']): FieldDef[] {
  return [
    toMatchFieldDef({ key: 'eventTypes', label: 'Type', multiple: true }),
    toMatchFieldDef({ admits, key: 'eventSubtypes', label: 'Subtype', multiple: true }),
  ];
}

const admitsSubtypes: FieldDef['admits'] = values =>
  (values.eventTypes ?? []).flatMap(type => SUBTYPES[type] ?? []);

function state(types: string[], subtypes: string[]): FilterState {
  return [
    { fieldKey: 'eventTypes', op: 'is', values: types },
    { fieldKey: 'eventSubtypes', op: 'is', values: subtypes },
  ];
}

describe('pruneInadmissible', () => {
  it('should drop a value the other field no longer admits', () => {
    const pruned = pruneInadmissible(state(['spend'], ['fee', 'airdrop']), fields(admitsSubtypes));

    expect(pruned).toStrictEqual([
      { fieldKey: 'eventTypes', op: 'is', values: ['spend'] },
      { fieldKey: 'eventSubtypes', op: 'is', values: ['fee'] },
    ]);
  });

  // An empty pill filters nothing, and leaving one behind would read as an active filter.
  it('should remove the filter entirely when no value survives', () => {
    const pruned = pruneInadmissible(state(['spend'], ['airdrop']), fields(admitsSubtypes));

    expect(pruned).toStrictEqual([{ fieldKey: 'eventTypes', op: 'is', values: ['spend'] }]);
  });

  it('should keep values the other field still admits', () => {
    const input = state(['spend', 'receive'], ['fee', 'airdrop']);

    expect(pruneInadmissible(input, fields(admitsSubtypes))).toBe(input);
  });

  // The option lists are store-backed, so "nothing admitted" is indistinguishable from "the mapping
  // has not loaded". Wiping the user's selection on a cold start is the worse reading.
  it('should admit everything when the field knows of no values yet', () => {
    const input = state(['spend'], ['fee', 'airdrop']);

    expect(pruneInadmissible(input, fields(() => []))).toBe(input);
  });

  it('should return the same state when no field declares admits', () => {
    const input = state(['spend'], ['airdrop']);

    expect(pruneInadmissible(input, fields())).toBe(input);
  });

  it('should leave a field with no values alone', () => {
    const input: FilterState = [{ fieldKey: 'eventSubtypes', op: 'is', values: [] }];

    expect(pruneInadmissible(input, fields(admitsSubtypes))).toBe(input);
  });
});
