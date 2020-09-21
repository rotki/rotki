export const YEARN_YCRV_VAULT = 'YCRV Vault';
export const YEARN_DAI_VAULT = 'YDAI Vault';
export const YEARN_WETH_VAULT = 'YWETH Vault';
export const YEARN_YFI_VAULT = 'YYFI Vault';
export const YEARN_ALINK_VAULT = 'YALINK Vault';
export const YEARN_USDT_VAULT = 'YUSDT Vault';
export const YEARN_USDC_VAULT = 'YUSDC Vault';
export const YEARN_TUSD_VAULT = 'YTUSD Vault';
export const YEARN_BCURVE_VAULT = 'YBCURVE Vault';
export const YEARN_SRENCURVE_VAULT = 'YSRENCURVE Vault';

export const YEARN_VAULTS = [
  YEARN_YCRV_VAULT,
  YEARN_DAI_VAULT,
  YEARN_WETH_VAULT,
  YEARN_YFI_VAULT,
  YEARN_ALINK_VAULT,
  YEARN_USDT_VAULT,
  YEARN_USDC_VAULT,
  YEARN_TUSD_VAULT,
  YEARN_BCURVE_VAULT,
  YEARN_SRENCURVE_VAULT
] as const;

export const WITHDRAW = 'withdraw';
export const DEPOSIT = 'deposit';

export const YEARN_EVENTS = [WITHDRAW, DEPOSIT] as const;
