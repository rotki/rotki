import type { SolanaTokenMigrationData } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-dialog';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { useSolanaTokenMigrationDialog } from './use-solana-token-migration-dialog';

const { migrateSolanaToken, removeIdentifier, setMessage } = vi.hoisted(() => ({
  migrateSolanaToken: vi.fn(),
  removeIdentifier: vi.fn(),
  setMessage: vi.fn(),
}));

vi.mock('@/modules/assets/admin/solana-token-migration/solana-token-migration', () => ({
  useSolanaTokenMigrationApi: (): Record<string, unknown> => ({ migrateSolanaToken }),
}));

vi.mock('@/modules/assets/admin/solana-token-migration/use-solana-token-migration-store', () => ({
  useSolanaTokenMigrationStore: (): Record<string, unknown> => ({ removeIdentifier }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

const TARGET = 'solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const UNIQUE_CONSTRAINT = `UNIQUE constraint failed: assets.identifier ${TARGET}`;

let modelValue: Ref<SolanaTokenMigrationData | undefined>;
let oldAsset: Ref<string | undefined>;
let onMigrated: ReturnType<typeof vi.fn<() => void>>;
let onSuggestMerge: ReturnType<typeof vi.fn<(suggestion: { sourceAsset: string; targetAsset: string }) => void>>;
let validateForm: ReturnType<typeof vi.fn<() => boolean>>;
let scope: ReturnType<typeof effectScope>;

function dialog(): ReturnType<typeof useSolanaTokenMigrationDialog> {
  scope = effectScope();
  return scope.run(() => useSolanaTokenMigrationDialog({
    modelValue,
    oldAsset,
    onMigrated,
    onSuggestMerge,
    validateForm,
  }))!;
}

describe('modules/assets/admin/solana-token-migration/useSolanaTokenMigrationDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    modelValue = ref<SolanaTokenMigrationData>({ address: 'So111', decimals: 9, tokenKind: 'spl-token' });
    oldAsset = ref<string>('SOL-OLD');
    onMigrated = vi.fn<() => void>();
    onSuggestMerge = vi.fn<(suggestion: { sourceAsset: string; targetAsset: string }) => void>();
    validateForm = vi.fn<() => boolean>(() => true);
    migrateSolanaToken.mockResolvedValue(true);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('before it migrates anything', () => {
    it('should migrate nothing without a target token', async () => {
      set(modelValue, undefined);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(migrateSolanaToken).not.toHaveBeenCalled();
    });

    it('should migrate nothing without an asset to migrate from', async () => {
      set(oldAsset, undefined);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(migrateSolanaToken).not.toHaveBeenCalled();
    });

    it('should migrate nothing while the form is invalid', async () => {
      validateForm.mockReturnValue(false);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(migrateSolanaToken).not.toHaveBeenCalled();
    });

    it('should migrate nothing without decimals, and say why', async () => {
      set(modelValue, { address: 'So111', decimals: null, tokenKind: 'spl-token' });

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(migrateSolanaToken).not.toHaveBeenCalled();
      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({
        description: 'asset_management.solana_token_migration.validation_error',
      }));
    });
  });

  describe('a migration that lands', () => {
    it('should send the token and the asset it replaces', async () => {
      const { save } = dialog();
      await save();

      expect(migrateSolanaToken).toHaveBeenCalledWith({
        address: 'So111',
        decimals: 9,
        oldAsset: 'SOL-OLD',
        tokenKind: 'spl-token',
      });
    });

    it('should drop the migrated identifier and tell the caller to refresh', async () => {
      const { save } = dialog();

      expect(await save()).toBe(true);
      expect(removeIdentifier).toHaveBeenCalledWith('SOL-OLD');
      expect(onMigrated).toHaveBeenCalledOnce();
      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ success: true }));
    });

    it('should clear the dialog', async () => {
      const { save } = dialog();
      await save();

      expect(get(modelValue)).toBeUndefined();
      expect(get(oldAsset)).toBeUndefined();
    });

    it('should mark itself loading only while the migration runs', async () => {
      const { loading, save } = dialog();

      const pending = save();
      expect(get(loading)).toBe(true);

      await pending;
      expect(get(loading)).toBe(false);
    });
  });

  describe('a migration the backend refuses', () => {
    it('should report it and keep the dialog open', async () => {
      migrateSolanaToken.mockResolvedValue(false);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(removeIdentifier).not.toHaveBeenCalled();
      expect(onMigrated).not.toHaveBeenCalled();
      expect(get(modelValue)).toBeDefined();
    });

    it('should stop loading so the user can try again', async () => {
      migrateSolanaToken.mockRejectedValue(new Error('boom'));

      const { loading, save } = dialog();
      await save();

      expect(get(loading)).toBe(false);
    });

    it('should report a plain failure as a message', async () => {
      migrateSolanaToken.mockRejectedValue(new Error('the chain is unreachable'));

      const { save } = dialog();
      await save();

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({
        description: 'the chain is unreachable',
      }));
    });

    it('should put field errors on the form rather than in a message', async () => {
      migrateSolanaToken.mockRejectedValue(
        new ApiValidationError(JSON.stringify({ address: ['not a valid address'] })),
      );

      const { modelErrorMessages, save } = dialog();
      await save();

      expect(get(modelErrorMessages)).toEqual({ address: ['not a valid address'] });
      expect(validateForm).toHaveBeenCalledTimes(2);
      expect(setMessage).not.toHaveBeenCalled();
    });
  });

  describe('a collision with an asset that already exists', () => {
    it('should offer a merge instead of reporting an error', async () => {
      migrateSolanaToken.mockRejectedValue(new Error(UNIQUE_CONSTRAINT));

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(onSuggestMerge).toHaveBeenCalledWith({ sourceAsset: 'SOL-OLD', targetAsset: TARGET });
      expect(setMessage).not.toHaveBeenCalled();
    });

    it('should hand the dialog over by clearing its selection', async () => {
      migrateSolanaToken.mockRejectedValue(new Error(UNIQUE_CONSTRAINT));

      const { save } = dialog();
      await save();

      expect(get(modelValue)).toBeUndefined();
      expect(get(oldAsset)).toBeUndefined();
    });

    it('should report the error when the collision names no asset it recognises', async () => {
      migrateSolanaToken.mockRejectedValue(new Error('UNIQUE constraint failed: assets.identifier'));

      const { save } = dialog();
      await save();

      expect(onSuggestMerge).not.toHaveBeenCalled();
      expect(setMessage).toHaveBeenCalledOnce();
      expect(get(modelValue)).toBeDefined();
    });

    it('should not read a merge out of an unrelated failure', async () => {
      migrateSolanaToken.mockRejectedValue(new Error(`something else went wrong ${TARGET}`));

      const { save } = dialog();
      await save();

      expect(onSuggestMerge).not.toHaveBeenCalled();
      expect(setMessage).toHaveBeenCalledOnce();
    });
  });
});
