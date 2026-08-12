import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { withSetup } from '@test/utils/with-setup';
import { describe, expect, it } from 'vitest';
import { routeSchemaFromFields } from '@/modules/core/table/route';
import { useEthValidatorFields } from './use-eth-validator-fields';
import '@test/i18n';

function fields(): FieldDef[] {
  setActivePinia(createCustomPinia());
  const { result, wrapper } = withSetup(() => useEthValidatorFields());
  const built = get(result);
  wrapper.unmount();
  return built;
}

function fieldOf(key: string): FieldDef | undefined {
  return fields().find(field => field.key === key);
}

describe('useEthValidatorFields', () => {
  // The url shape of the filter bag is derived from these fields, so the round-trip is asserted
  // here rather than against a second hand-written declaration.
  describe('route query', () => {
    it('should coerce single route values into arrays', () => {
      expect(routeSchemaFromFields(fields()).parse({ index: '5', publicKey: '0xabc', status: 'active' }))
        .toEqual({ index: ['5'], publicKey: ['0xabc'], status: ['active'] });
    });

    it('should keep array route values as arrays', () => {
      expect(routeSchemaFromFields(fields()).parse({ status: ['active', 'exited'] }))
        .toEqual({ status: ['active', 'exited'] });
    });

    it('should allow an empty route filter', () => {
      expect(routeSchemaFromFields(fields()).parse({})).toEqual({});
    });
  });

  it('should send the keys the validators request takes', () => {
    expect(fields().map(field => field.key)).toStrictEqual(['index', 'publicKey', 'status']);
  });

  it('should offer every status except all', () => {
    const status = fieldOf('status');

    // `all` is the absence of the pill, so offering it would be a second way to say the same thing.
    expect(status?.suggest?.()).toStrictEqual(['exited', 'active', 'consolidated']);
    expect(status?.multiple).toBe(true);
  });

  it('should read a status as a word rather than its raw value', () => {
    expect(fieldOf('status')?.resolveLabel?.('consolidated')).toBe('Consolidated');
  });

  // Both are written, since neither has a list worth offering: an index is a number the user knows
  // and a public key is pasted.
  it('should apply an index only when it is one', () => {
    const index = fieldOf('index');

    expect(index?.freeText).toBe(true);
    expect(index?.validate?.(' 42 ')).toBe(true);
    expect(index?.validate?.('0x42')).toBe(false);
  });

  it('should refuse a half-pasted public key', () => {
    const publicKey = fieldOf('publicKey');

    expect(publicKey?.freeText).toBe(true);
    expect(publicKey?.validate?.(`0x${'a'.repeat(96)}`)).toBe(true);
    expect(publicKey?.validate?.(`0x${'a'.repeat(40)}`)).toBe(false);
  });

  // None of these keys is declared as behaviour-carrying, so the request has no form for an
  // exclusion and the pill must not offer one.
  it('should offer no exclusion on any field', () => {
    for (const field of fields()) {
      expect(field.allowExclusion).toBe(false);
      expect(field.operators).not.toContain('is_not');
    }
  });
});
