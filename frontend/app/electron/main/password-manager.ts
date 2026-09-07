import type { Credentials } from '@shared/ipc';
import { Buffer } from 'node:buffer';
import path from 'node:path';
import { PasswordStore } from '@electron/main/password-store';
import { app, safeStorage } from 'electron';

const ENCODING = 'latin1';

export class PasswordManager {
  private readonly store = new PasswordStore(path.join(app.getPath('userData'), 'config.json'));

  private readonly getEncryptionAvailability = (): boolean => safeStorage.isEncryptionAvailable();

  private readonly setPassword = (key: string, password: string) => {
    const buffer = safeStorage.encryptString(password);
    this.store.set(key, buffer.toString(ENCODING));
  };

  private readonly clearPassword = () => {
    this.store.clear();
  };

  private readonly hasStoredPassword = (key: string): boolean => Boolean(this.store.get(key));

  private readonly hasAnyStoredPassword = (): boolean => !this.store.isEmpty();

  private readonly getPassword = (key: string) => {
    const buffer = this.store.get(key);
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

  /**
   * Reads back a password saved by {@link storePassword}.
   *
   * @remarks
   * The on-disk store is probed before `safeStorage`, because touching `safeStorage` can raise an
   * OS keyring prompt. A user who never opted into saving a password must never see that prompt,
   * so the order of these two guards is the behaviour, not an optimization.
   *
   * @returns the decrypted password, or an empty string when none is stored for this user or the
   * platform cannot decrypt it.
   */
  async retrievePassword(username: string): Promise<string> {
    if (!this.hasStoredPassword(username))
      return '';

    if (!this.getEncryptionAvailability())
      return '';

    return this.getPassword(username);
  }

  /**
   * Removes every saved password.
   *
   * @remarks
   * Clearing the on-disk store needs no `safeStorage`, so the emptiness check keeps a user with
   * nothing saved from being shown an OS keyring prompt on their way out.
   */
  async clearPasswords(): Promise<void> {
    if (this.hasAnyStoredPassword())
      this.clearPassword();
  }
}
