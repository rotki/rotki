import type { EIP1193Provider, EIP6963AnnounceProviderEvent, EIP6963ProviderDetail, Permission } from '@/types';
import { assert } from '@rotki/common';
import { uniqueObjects } from '@/utils/data';

export async function getAllBrowserWalletProviders(): Promise<EIP6963ProviderDetail[]> {
  return new Promise((resolve) => {
    const providers: EIP6963ProviderDetail[] = [];

    function handleProviderAnnouncement(event: EIP6963AnnounceProviderEvent): void {
      providers.push(event.detail);
    }

    function cleanup(): void {
      window.removeEventListener('eip6963:announceProvider', handleProviderAnnouncement);
    }

    window.addEventListener('eip6963:announceProvider', handleProviderAnnouncement);
    window.dispatchEvent(new Event('eip6963:requestProvider'));

    setTimeout(() => {
      cleanup();
      resolve(uniqueObjects(providers, item => item.info.uuid));
    }, 1000);
  });
}

export async function getAddressesFromWallet(provider: EIP1193Provider): Promise<string[]> {
  const permissions = await provider.request<Permission[]>({
    method: 'wallet_requestPermissions',
    params: [
      {
        eth_accounts: {},
      },
    ],
  });

  const accountPermission = permissions.find(permission => permission.parentCapability === 'eth_accounts');

  assert(accountPermission);

  const requestedAddresses = await provider.request<string[]>({
    method: 'eth_requestAccounts',
    params: [],
  });

  const addresses: string[] = [];
  requestedAddresses.forEach((item) => {
    addresses.push(item);
  });

  assert(addresses);
  return addresses;
}
