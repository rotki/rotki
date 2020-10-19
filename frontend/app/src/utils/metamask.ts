import { assert } from '@/utils/assertions';

export function metamaskImportEnabled(): boolean {
  return (
    (!!window.interop || (window.ethereum && window.ethereum.isMetaMask)) ??
    false
  );
}

export async function getMetamaskAddresses(): Promise<string[]> {
  assert(window.ethereum);
  assert(window.ethereum.isMetaMask);

  const permissions = await window.ethereum.request({
    method: 'wallet_requestPermissions',
    params: [
      {
        eth_accounts: {}
      }
    ]
  });

  const accountPermission = permissions.find(
    permission => permission.parentCapability === 'eth_accounts'
  );

  assert(accountPermission);

  const exposedAccounts = accountPermission.caveats.find(
    caveat => caveat.name === 'exposedAccounts'
  );

  assert(exposedAccounts);
  return exposedAccounts.value;
}
