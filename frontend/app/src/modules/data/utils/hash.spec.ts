import { describe, expect, it } from 'vitest';
import { createDatabaseIdentifier, createShortHash } from './hash';

describe('createShortHash', () => {
  it('returns a 6-character string', () => {
    const hash = createShortHash('/home/user/data');
    expect(hash).toHaveLength(6);
  });

  it('is deterministic - same input produces same output', () => {
    const input = '/home/user/data/rotki';
    const hash1 = createShortHash(input);
    const hash2 = createShortHash(input);
    expect(hash1).toBe(hash2);
  });

  it('produces different hashes for different inputs', () => {
    const hash1 = createShortHash('/path/one');
    const hash2 = createShortHash('/path/two');
    expect(hash1).not.toBe(hash2);
  });

  it('handles empty string', () => {
    const hash = createShortHash('');
    expect(hash).toHaveLength(6);
    expect(hash).toBe('000000');
  });

  it('returns alphanumeric string', () => {
    const hash = createShortHash('/some/data/directory');
    expect(hash).toMatch(/^[\da-z]+$/);
  });
});

describe('createDatabaseIdentifier', () => {
  it('creates identifier in format: {hash}.{username}', () => {
    const identifier = createDatabaseIdentifier('/data/dir', 'testuser');
    expect(identifier).toMatch(/^[\da-z]{6}\.testuser$/);
  });

  it('uses only dataDirectory for hash, not username', () => {
    const id1 = createDatabaseIdentifier('/same/path', 'user1');
    const id2 = createDatabaseIdentifier('/same/path', 'user2');

    const hash1 = id1.split('.')[0];
    const hash2 = id2.split('.')[0];

    expect(hash1).toBe(hash2);
  });

  it('different dataDirectory produces different hash', () => {
    const id1 = createDatabaseIdentifier('/path/one', 'sameuser');
    const id2 = createDatabaseIdentifier('/path/two', 'sameuser');

    const hash1 = id1.split('.')[0];
    const hash2 = id2.split('.')[0];

    expect(hash1).not.toBe(hash2);
  });

  it('preserves username in identifier', () => {
    const identifier = createDatabaseIdentifier('/any/path', 'myuser123');
    expect(identifier).toContain('.myuser123');
  });
});
