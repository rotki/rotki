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
    let password = '';
    if (this.getEncryptionAvailability())
      password = this.getPassword(username);

    return password;
  }

  async clearPasswords(): Promise<void> {
    if (this.getEncryptionAvailability())
      this.clearPassword();
  }
}
