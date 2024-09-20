const BASE_URL = 'https://rotki.com/';
const OLD_DOCS_BASE_URL = 'https://rotki.readthedocs.io/en/stable/';
const DOCS_BASE_URL = 'https://docs.rotki.com/';
const USAGE_GUIDE_URL = `${DOCS_BASE_URL}usage-guides/`;
const CONTRIBUTE_URL = `${DOCS_BASE_URL}contribution-guides/`;
const GITHUB_BASE_URL = 'https://github.com/rotki/rotki/';

// Cannot be checked with fetch because it always returns 400
export const TWITTER_URL = 'https://twitter.com/rotkiapp';

// Cannot be checked with fetch because it always returns 403, because it needs authentication,
// and will be redirected to the register page instead
export const etherscanLinks = {
  ethereum: 'https://etherscan.io/myapikey',
  optimism: 'https://optimistic.etherscan.io/myapikey',
  polygonPos: 'https://polygonscan.com/myapikey',
  arbitrumOne: 'https://arbiscan.io/myapikey',
  base: 'https://basescan.org/myapikey',
  gnosis: 'https://gnosisscan.io/myapikey',
  scroll: 'https://scrollscan.com/myapikey',
};

export const externalLinks = {
  premium: `${BASE_URL}products`,
  usageGuide: USAGE_GUIDE_URL,
  usageGuideSection: {
    dockerWarning: `${USAGE_GUIDE_URL}using-rotki-from-mobile#docker`,
    addingAnExchange: `${USAGE_GUIDE_URL}importing-data#adding-an-exchange`,
    theGraphApiKey: `${USAGE_GUIDE_URL}importing-data#the-graph`,
    gnosisPayKey: `${USAGE_GUIDE_URL}importing-data#gnosis-pay`,
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
  liquityTotalCollateralRatioDoc: 'https://docs.liquity.org/faq/recovery-mode#what-is-the-total-collateral-ratio',
};
