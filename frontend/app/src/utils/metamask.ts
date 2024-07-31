import type { EIP1193Provider, EIP6963AnnounceProviderEvent } from '@/types';

export function isMetaMaskSupported(): boolean {
  return (
    (!!window.interop || (window.ethereum && window.ethereum.isMetaMask))
    ?? false
  );
}

function getMetamaskProviderWithTimeout(timeout = 2000): Promise<EIP1193Provider | undefined> {
  return new Promise((resolve) => {
    let provider;

    const handleProviderAnnouncement = (event: EIP6963AnnounceProviderEvent) => {
      if (event.detail.info.rdns === 'io.metamask') {
        provider = event.detail.provider;
        cleanup();
        resolve(provider);
      }
    };

    const cleanup = () => {
      window.removeEventListener('eip6963:announceProvider', handleProviderAnnouncement);
    };

    window.addEventListener('eip6963:announceProvider', handleProviderAnnouncement);
    window.dispatchEvent(new Event('eip6963:requestProvider'));

    setTimeout(() => {
      cleanup();
      resolve(undefined);
    }, timeout);
  });
}

export async function getMetamaskAddresses(): Promise<string[]> {
  assert(window.ethereum);
  assert(window.ethereum.isMetaMask);

  const provider = await getMetamaskProviderWithTimeout();
  assert(provider);

  const permissions = await provider.request({
    method: 'wallet_requestPermissions',
    params: [
      {
        eth_accounts: {},
      },
    ],
  });

  const accountPermission = permissions.find(
    permission => typeof permission !== 'string' && permission.parentCapability === 'eth_accounts',
  );

  assert(accountPermission);

  const requestedAddresses = await provider.request({
    method: 'eth_requestAccounts',
    params: [],
  });

  const addresses: string[] = [];
  requestedAddresses.forEach((item) => {
    if (typeof item === 'string')
      addresses.push(item);
  });

  assert(addresses);
  return addresses;
}
