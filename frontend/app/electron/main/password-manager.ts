import type { Credentials } from '@shared/ipc';
import { Buffer } from 'node:buffer';
import { safeStorage } from 'electron';
import Store from 'electron-store';

const ENCODING = 'latin1';

export class PasswordManager {
  private readonly store = new Store<Record<string, string>>();

  private readonly getEncryptionAvailability = (): boolean => safeStorage.isEncryptionAvailable();

  private readonly setPassword = (key: string, password: string) => {
    const buffer = safeStorage.encryptString(password);
    this.store.set(key, buffer.toString(ENCODING));
  };

  private readonly clearPassword = () => {
    this.store.clear();
  };

  private readonly hasStoredPassword = (key: string): boolean => Boolean(this.store.store?.[key]);

  private readonly hasAnyStoredPassword = (): boolean => Object.keys(this.store.store ?? {}).length > 0;

  private readonly getPassword = (key: string) => {
    const buffer = this.store.store?.[key];
    if (buffer)
      return safeStorage.decryptString(Buffer.from(buffer, ENCODING));

    return '';
  };

  async storePassword({ username, password }: Credentials): Promise<boolean> {
    let success = false;
    if (this.getEncryptionAvailability()) {
      this.setPassword(username, password);
      success = true;
    }
    return success;
  }

  async retrievePassword(username: string): Promise<string> {
    // Never touch safeStorage (which triggers an OS keyring prompt) unless a
    // password was actually saved for this user. If nothing is stored, the user
    // never opted in to saving the password, so there is nothing to decrypt.
    if (!this.hasStoredPassword(username))
      return '';

    if (!this.getEncryptionAvailability())
      return '';

    return this.getPassword(username);
  }

  async clearPasswords(): Promise<void> {
    // Clearing the on-disk store does not require safeStorage; only access the
    // keyring when there is actually a saved password to clear.
    if (this.hasAnyStoredPassword())
      this.clearPassword();
  }
}
