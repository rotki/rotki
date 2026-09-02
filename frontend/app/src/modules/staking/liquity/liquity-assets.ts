/** The stability pool is denominated in LUSD, so its totals are priced against this asset. */
export const LUSD_ID = 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0';

/** The staking and reward token. */
const LQTY_ID = 'eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D';

/**
 * Every asset a liquity position can be denominated in.
 *
 * @remarks
 * Pre-fetched by the page so the statistics have prices to re-value against without a per-row
 * lookup.
 */
export const LIQUITY_PRICED_ASSETS = [LUSD_ID, LQTY_ID, 'ETH'];
