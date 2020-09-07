export enum Status {
  NONE,
  LOADING,
  REFRESHING,
  PARTIALLY_LOADED,
  LOADED
}

export enum Section {
  NONE = 'none',
  ASSET_MOVEMENT = 'asset_movement',
  TRADES = 'trades',
  TX = 'tx',
  DEFI_COMPOUND_BALANCES = 'defi_compound_balances',
  DEFI_COMPOUND_HISTORY = 'defi_compound_history'
}
