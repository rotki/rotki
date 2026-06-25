import { Buffer } from 'node:buffer';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PasswordManager } from './password-manager';

const ENCODING = 'latin1';

const { isEncryptionAvailable, encryptString, decryptString, backing } = vi.hoisted(() => ({
  isEncryptionAvailable: vi.fn<() => boolean>(),
  encryptString: vi.fn<(value: string) => Buffer>(),
  decryptString: vi.fn<(buffer: Buffer) => string>(),
  backing: { data: {} as Record<string, string> },
}));

vi.mock('electron', () => ({
  safeStorage: { isEncryptionAvailable, encryptString, decryptString },
}));

vi.mock('electron-store', () => ({
  default: class {
    get store(): Record<string, string> {
      return backing.data;
    }

    set(key: string, value: string): void {
      backing.data[key] = value;
    }

    clear(): void {
      backing.data = {};
    }
  },
}));

describe('passwordManager', () => {
  let manager: PasswordManager;

  beforeEach(() => {
    vi.clearAllMocks();
    backing.data = {};
    manager = new PasswordManager();
  });

  describe('retrievePassword', () => {
    it('should not touch safeStorage when no password is stored for the user', async () => {
      // Regression: creating/using an account without opting in to "save password"
      // must never trigger an OS keyring prompt. With nothing stored, safeStorage
      // (including isEncryptionAvailable, which is what prompts on macOS) must not
      // be accessed at all.
      const password = await manager.retrievePassword('alice');

      expect(password).toBe('');
      expect(isEncryptionAvailable).not.toHaveBeenCalled();
      expect(decryptString).not.toHaveBeenCalled();
    });

    it('should not touch safeStorage when a different user has a stored password', async () => {
      backing.data.bob = 'encrypted-blob-for-bob';

      const password = await manager.retrievePassword('alice');

      expect(password).toBe('');
      expect(isEncryptionAvailable).not.toHaveBeenCalled();
      expect(decryptString).not.toHaveBeenCalled();
    });

    it('should decrypt the stored password when one exists', async () => {
      backing.data.alice = 'encrypted-blob';
      isEncryptionAvailable.mockReturnValue(true);
      decryptString.mockReturnValue('s3cret');

      const password = await manager.retrievePassword('alice');

      expect(password).toBe('s3cret');
      expect(isEncryptionAvailable).toHaveBeenCalledOnce();
      expect(decryptString).toHaveBeenCalledWith(Buffer.from('encrypted-blob', ENCODING));
    });

    it('should not decrypt when encryption is unavailable even if a password is stored', async () => {
      backing.data.alice = 'encrypted-blob';
      isEncryptionAvailable.mockReturnValue(false);

      const password = await manager.retrievePassword('alice');

      expect(password).toBe('');
      expect(decryptString).not.toHaveBeenCalled();
    });
  });

  describe('storePassword', () => {
    it('should encrypt and store the password when encryption is available', async () => {
      isEncryptionAvailable.mockReturnValue(true);
      encryptString.mockReturnValue(Buffer.from('encrypted', ENCODING));

      const success = await manager.storePassword({ username: 'alice', password: 's3cret' });

      expect(success).toBe(true);
      expect(encryptString).toHaveBeenCalledWith('s3cret');
      expect(backing.data.alice).toBe('encrypted');
    });

    it('should not store the password when encryption is unavailable', async () => {
      isEncryptionAvailable.mockReturnValue(false);

      const success = await manager.storePassword({ username: 'alice', password: 's3cret' });

      expect(success).toBe(false);
      expect(encryptString).not.toHaveBeenCalled();
      expect(backing.data.alice).toBeUndefined();
    });
  });

  describe('clearPasswords', () => {
    it('should not touch safeStorage when there is nothing stored', async () => {
      await manager.clearPasswords();

      expect(isEncryptionAvailable).not.toHaveBeenCalled();
    });

    it('should clear stored passwords when present', async () => {
      backing.data.alice = 'encrypted-blob';

      await manager.clearPasswords();

      expect(backing.data).toStrictEqual({});
    });
  });
});
