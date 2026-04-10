const DOCS_SUBFOLDER = !import.meta.env?.DEV ? '' : 'latest/';
const BASE_URL = 'https://rotki.com/';
const OLD_DOCS_BASE_URL = 'https://rotki.readthedocs.io/en/stable/';
const DOCS_BASE_URL = `https://docs.rotki.com/${DOCS_SUBFOLDER}`;
const USAGE_GUIDE_URL = `${DOCS_BASE_URL}usage-guides/`;
const CONTRIBUTE_URL = `${DOCS_BASE_URL}contribution-guides/`;
const GITHUB_BASE_URL = 'https://github.com/rotki/rotki/';
const UTM_PARAMS = '?utm_source=rotki_app&utm_medium=desktop&utm_campaign=upgrade';

// Cannot be checked with fetch because it always returns 400
export const TWITTER_URL = 'https://twitter.com/rotkiapp';

export const SUPPORT_EMAIL = 'support@rotki.com';

// Cannot be checked with fetch because it always returns 403, because it needs authentication,
// and will be redirected to the register page instead
export const etherscanLink = 'https://etherscan.io/myapikey';

export const heliusLink = 'https://dev.helius.xyz/dashboard/app';

export const blockscoutLink = 'https://api.blockscout.com/account/api-key';

export const externalLinks = {
  premium: `${BASE_URL}products${UTM_PARAMS}`,
  premiumDevices: `${DOCS_BASE_URL}premium/devices`,
  sponsor: `${BASE_URL}sponsor/mint`,
  manageSubscriptions: `${BASE_URL}home/subscription${UTM_PARAMS}`,
  usageGuide: USAGE_GUIDE_URL,
  usageGuideSection: {
    dockerWarning: `${USAGE_GUIDE_URL}advanced/mobile#docker`,
    addingAnExchange: `${USAGE_GUIDE_URL}integrations/exchange-keys#exchanges-api-keys`,
    theGraphApiKey: `${USAGE_GUIDE_URL}integrations/external-services#the-graph`,
    gnosisPayKey: `${USAGE_GUIDE_URL}integrations/external-services#gnosis-pay`,
    importBlockchainAccounts: `${USAGE_GUIDE_URL}portfolio/accounts#import-and-export-blockchain-accounts-csv`,
    importAddressBook: `${USAGE_GUIDE_URL}data-management/address-book#importing-address-book-names-csv`,
    solanaTokenMigration: `${GITHUB_BASE_URL}releases/tag/v1.40.0`,
  },
  coingeckoAsset: `https://www.coingecko.com/en/coins/$symbol`,
  cryptocompareAsset: `https://www.cryptocompare.com/coins/$symbol/overview`,
  contribute: CONTRIBUTE_URL,
  contributeSection: {
    coingecko: `${CONTRIBUTE_URL}contribute-as-developer#get-coingecko-asset-identifier`,
    cryptocompare: `${CONTRIBUTE_URL}contribute-as-developer#get-cryptocompare-asset-identifier`,
    language: `${CONTRIBUTE_URL}contribute-as-developer#add-a-new-language-or-translation`,
  },
  faq: `${DOCS_BASE_URL}faq`,
  changeLog: `${OLD_DOCS_BASE_URL}changelog.html`,
  discord: 'https://discord.rotki.com',
  github: GITHUB_BASE_URL,
  githubIssues: `${GITHUB_BASE_URL}issues`,
  githubNewIssue: `${GITHUB_BASE_URL}issues/new/choose`,
  githubNewBugReport: `${GITHUB_BASE_URL}issues/new?template=bug_report.md`,
  gmailCompose: 'https://mail.google.com/mail/?view=cm',
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
  beaconChainApiKey: 'https://beaconcha.in/user/settings',
};
