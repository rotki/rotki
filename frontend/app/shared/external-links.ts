const DOCS_SUBFOLDER = !import.meta.env?.DEV ? '' : 'latest/';
const BASE_URL = 'https://rotki.com/';
const OLD_DOCS_BASE_URL = 'https://rotki.readthedocs.io/en/stable/';
const DOCS_BASE_URL = `https://docs.rotki.com/${DOCS_SUBFOLDER}`;
const USAGE_GUIDE_URL = `${DOCS_BASE_URL}usage-guides/`;
const CONTRIBUTE_URL = `${DOCS_BASE_URL}contribution-guides/`;
const GITHUB_BASE_URL = 'https://github.com/rotki/rotki/';

// Cannot be checked with fetch because it always returns 400
export const TWITTER_URL = 'https://twitter.com/rotkiapp';

// Cannot be checked with fetch because it always returns 403, because it needs authentication,
// and will be redirected to the register page instead
export const etherscanLink = 'https://etherscan.io/myapikey';

export const blockscoutLinks = {
  ethereum: 'https://eth.blockscout.com/account/api-key',
  optimism: 'https://optimism.blockscout.com/account/api-key',
  polygonPos: 'https://polygon.blockscout.com/account/api-key',
  arbitrumOne: 'https://arbitrum.blockscout.com/account/api-key',
  base: 'https://base.blockscout.com/account/api-key',
  gnosis: 'https://gnosis.blockscout.com/account/api-key',
};

export const externalLinks = {
  premium: `${BASE_URL}products`,
  usageGuide: USAGE_GUIDE_URL,
  usageGuideSection: {
    dockerWarning: `${USAGE_GUIDE_URL}using-rotki-from-mobile#docker`,
    addingAnExchange: `${USAGE_GUIDE_URL}api-keys#exchanges-api-keys`,
    theGraphApiKey: `${USAGE_GUIDE_URL}api-keys#the-graph`,
    gnosisPayKey: `${USAGE_GUIDE_URL}api-keys#gnosis-pay`,
    importBlockchainAccounts: `${USAGE_GUIDE_URL}accounts-and-balances#import-and-export-blockchain-accounts-csv`,
    importAddressBook: `${USAGE_GUIDE_URL}address-book#importing-address-book-names-csv`,
    solanaTokenMigration: `${USAGE_GUIDE_URL}solana-tokens-migration`,
  },
  coingeckoAsset: `https://www.coingecko.com/en/coins/$symbol`,
  cryptocompareAsset: `https://www.cryptocompare.com/coins/$symbol/overview`,
  contribute: CONTRIBUTE_URL,
  contributeSection: {
    coingecko: `${CONTRIBUTE_URL}contribute-as-developer#get-coingecko-asset-identifier`,
    cryptocompare: `${CONTRIBUTE_URL}contribute-as-developer#get-cryptocompare-asset-identifier`,
    language: `${CONTRIBUTE_URL}contribute-as-developer.html#add-a-new-language-or-translation`,
  },
  faq: `${DOCS_BASE_URL}faq`,
  changeLog: `${OLD_DOCS_BASE_URL}changelog.html`,
  discord: 'https://discord.rotki.com',
  github: GITHUB_BASE_URL,
  githubIssues: `${GITHUB_BASE_URL}issues`,
  githubNewIssue: `${GITHUB_BASE_URL}issues/new/choose`,
  releases: `${GITHUB_BASE_URL}releases`,
  releasesVersion: `${GITHUB_BASE_URL}releases/tag/v$version`,
  metamaskDownload: 'https://metamask.io/download/',
  openSeaApiKeyReference: 'https://docs.opensea.io/reference/api-keys#how-do-i-get-an-api-key',
  nftWarning: 'https://medium.com/@alxlpsc/critical-privacy-vulnerability-getting-exposed-by-metamask-693c63c2ce94',
  binanceCsvExport: 'https://www.binance.com/en/my/wallet/history',
  applyTheGraphApiKey: 'https://thegraph.com/studio/apikeys/',
  liquityTotalCollateralRatioDoc: 'https://docs.liquity.org/liquity-v1/faq/recovery-mode#what-is-the-total-collateral-ratio',
  coingeckoApiKey: 'https://www.coingecko.com/en/api/pricing',
  defillamaApiKey: 'https://defillama.com/pro-api',
  alchemyApiKey: 'https://docs.alchemy.com/reference/api-overview',
};
