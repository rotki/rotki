import { MakerDAOVault, MakerDAOVaultDetails } from '@/services/types-model';

export type MakerDAOVaultModel =
  | MakerDAOVault
  | (MakerDAOVault & MakerDAOVaultDetails);
