export function isMetaMaskSupported(): boolean {
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

  const addresses: string[] = [];
  accountPermission.caveats.forEach(permission => {
    if (permission.value) {
      addresses.push(...permission.value);
    }
  });

  assert(addresses);
  return addresses;
}
