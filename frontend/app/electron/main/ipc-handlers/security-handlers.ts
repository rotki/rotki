import type { Credentials } from '@shared/ipc';
import { PasswordManager } from '@electron/main/password-manager';

export class SecurityHandlers {
  private readonly passwordManager = new PasswordManager();

  storePassword = async (credentials: Credentials): Promise<boolean> => this.passwordManager.storePassword(credentials);

  getPassword = async (username: string): Promise<string | undefined> => this.passwordManager.retrievePassword(username);

  clearPassword = async (): Promise<void> => this.passwordManager.clearPasswords();
}
