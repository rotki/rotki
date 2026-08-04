export function getAssetMovementsType(eventSubtype: string): 'deposit' | 'withdrawal' {
  if (eventSubtype === 'receive') {
    return 'deposit';
  }
  return 'withdrawal';
}
