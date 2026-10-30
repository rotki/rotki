export const STETH_IDENTIFIER = 'eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84';

/** Community staking modules rotki tracks, by their Lido StakingRouter module id. */
export const LidoCsmStakingModule = {
  CSM: 3,
  CSM_0X02: 5,
} as const;

export type LidoCsmStakingModule = (typeof LidoCsmStakingModule)[keyof typeof LidoCsmStakingModule];
