import type { LogService } from '@electron/main/log-service';
import { AddressImportServer } from '@electron/main/address-import-server';
import { selectPort } from '@electron/main/port-utils';
import { shell } from 'electron';

export class WalletImportHandlers {
  private walletImportTimeout: NodeJS.Timeout | undefined;
  private readonly addressImportServer: AddressImportServer;

  constructor(
    private readonly logger: LogService,
  ) {
    this.addressImportServer = new AddressImportServer(logger);
  }

  importFromWallet = async (): Promise<{ error: string } | { addresses: string[] }> => {
    try {
      const portNumber = await selectPort(40000);
      return await new Promise((resolve) => {
        const port = this.addressImportServer.start(
          addresses => resolve({ addresses }),
          portNumber,
        );

        shell.openExternal(`http://localhost:${port}`).catch((error) => {
          resolve({ error: error.message });
        });

        if (this.walletImportTimeout)
          clearTimeout(this.walletImportTimeout);

        this.walletImportTimeout = setTimeout(() => {
          this.addressImportServer.stop();
          resolve({ error: 'waiting timeout' });
        }, 120000);
      });
    }
    catch (error: any) {
      return { error: error.message };
    }
  };

  cleanup(): void {
    if (this.walletImportTimeout) {
      clearTimeout(this.walletImportTimeout);
      this.walletImportTimeout = undefined;
    }
  }
}
