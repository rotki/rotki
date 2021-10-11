import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { ApiMakerDAOVault } from '@/services/defi/types';
import { MakerDAOVault } from '@/store/defi/types';
import { bigNumberify } from '@/utils/bignumbers';

export function convertMakerDAOVaults(
  vaults: ApiMakerDAOVault[]
): MakerDAOVault[] {
  return vaults.map(vault => ({
    ...vault,
    identifier: vault.identifier.toString(),
    protocol: DefiProtocol.MAKERDAO_VAULTS,
    collateral: { ...vault.collateral, asset: vault.collateralAsset },
    collateralizationRatio: vault.collateralizationRatio ?? undefined,
    liquidationPrice: vault.liquidationPrice
      ? vault.liquidationPrice
      : bigNumberify(NaN)
  }));
}
