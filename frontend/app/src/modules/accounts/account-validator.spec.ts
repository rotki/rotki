import type { EthereumValidator, EthereumValidatorRequestPayload } from './blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { sortAndFilterValidators } from './account-validator';

function validator(overrides: Partial<EthereumValidator> = {}): EthereumValidator {
  return {
    amount: bigNumberify(32),
    index: 1,
    publicKey: '0xabc',
    status: 'active',
    type: 'validator',
    value: bigNumberify(64000),
    ...overrides,
  };
}

function payload(overrides: Partial<EthereumValidatorRequestPayload> = {}): EthereumValidatorRequestPayload {
  return {
    limit: 10,
    offset: 0,
    ...overrides,
  };
}

describe('sortAndFilterValidators', () => {
  const validators = (): EthereumValidator[] => [
    validator({ amount: bigNumberify(10), index: 1, publicKey: '0xaaa', status: 'active', value: bigNumberify(100) }),
    validator({ amount: bigNumberify(20), index: 2, publicKey: '0xbbb', status: 'exited', value: bigNumberify(200) }),
    validator({ amount: bigNumberify(30), index: 3, publicKey: '0xccc', status: 'active', value: bigNumberify(300) }),
  ];

  it('should return all validators when no filter is applied', () => {
    const result = sortAndFilterValidators(validators(), payload());
    expect(result.data).toHaveLength(3);
    expect(result.found).toBe(3);
    expect(result.total).toBe(3);
  });

  it('should compute the total value and amount over the filtered set', () => {
    const result = sortAndFilterValidators(validators(), payload());
    expect(result.totalValue?.toNumber()).toBe(600);
    expect(result.totalAmount?.toNumber()).toBe(60);
  });

  it('should filter by index', () => {
    const result = sortAndFilterValidators(validators(), payload({ index: ['2'] }));
    expect(result.data).toHaveLength(1);
    expect(result.data[0].index).toBe(2);
    expect(result.found).toBe(1);
    expect(result.total).toBe(3);
  });

  it('should filter by public key with partial match', () => {
    const result = sortAndFilterValidators(validators(), payload({ publicKey: ['ccc'] }));
    expect(result.data).toHaveLength(1);
    expect(result.data[0].publicKey).toBe('0xccc');
  });

  it('should filter by status', () => {
    const result = sortAndFilterValidators(validators(), payload({ status: ['active'] }));
    expect(result.data).toHaveLength(2);
    expect(result.data.map(v => v.index)).toEqual([1, 3]);
  });

  it('should require all provided filters to match', () => {
    const result = sortAndFilterValidators(validators(), payload({ index: ['1'], status: ['exited'] }));
    expect(result.data).toHaveLength(0);
    expect(result.found).toBe(0);
  });

  it('should only total the filtered validators', () => {
    const result = sortAndFilterValidators(validators(), payload({ status: ['active'] }));
    expect(result.totalValue?.toNumber()).toBe(400);
    expect(result.totalAmount?.toNumber()).toBe(40);
  });

  it('should sort ascending by an attribute', () => {
    const result = sortAndFilterValidators(validators(), payload({ ascending: [true], orderByAttributes: ['value'] }));
    expect(result.data.map(v => v.value.toNumber())).toEqual([100, 200, 300]);
  });

  it('should sort descending by an attribute', () => {
    const result = sortAndFilterValidators(validators(), payload({ ascending: [false], orderByAttributes: ['value'] }));
    expect(result.data.map(v => v.value.toNumber())).toEqual([300, 200, 100]);
  });

  it('should paginate using offset and limit', () => {
    const result = sortAndFilterValidators(validators(), payload({
      ascending: [true],
      limit: 1,
      offset: 1,
      orderByAttributes: ['index'],
    }));
    expect(result.data).toHaveLength(1);
    expect(result.data[0].index).toBe(2);
    expect(result.found).toBe(3);
  });

  it('should return an empty collection when there are no validators', () => {
    const result = sortAndFilterValidators([], payload());
    expect(result.data).toHaveLength(0);
    expect(result.total).toBe(0);
    expect(result.totalValue?.toNumber()).toBe(0);
    expect(result.totalAmount?.toNumber()).toBe(0);
  });
});
