import { describe, expect, it } from 'vitest';
import { extractTargetAssetFromError, isUniqueConstraintError } from './solana-migration-error';

const TARGET = 'solana/token:7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK';

describe('isUniqueConstraintError', () => {
  it('should detect the unique-constraint failure message', () => {
    expect(isUniqueConstraintError('UNIQUE constraint failed: assets.identifier')).toBe(true);
    expect(isUniqueConstraintError(`some prefix UNIQUE constraint failed: assets.identifier and ${TARGET}`)).toBe(true);
  });

  it('should return false for unrelated messages', () => {
    expect(isUniqueConstraintError('some other error')).toBe(false);
    expect(isUniqueConstraintError('UNIQUE constraint failed: assets.name')).toBe(false);
  });
});

describe('extractTargetAssetFromError', () => {
  it('should return the first solana token identifier in the message', () => {
    expect(extractTargetAssetFromError(`conflict with ${TARGET} already present`)).toBe(TARGET);
  });

  it('should return null when no solana token identifier is present', () => {
    expect(extractTargetAssetFromError('UNIQUE constraint failed: assets.identifier')).toBeNull();
    expect(extractTargetAssetFromError('')).toBeNull();
  });
});
