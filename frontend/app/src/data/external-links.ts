const BASE_URL = 'https://rotki.com/';
const DOCS_BASE_URL = 'https://rotki.readthedocs.io/en/stable/';
const USAGE_GUIDE_URL = `${DOCS_BASE_URL}/usage_guide.html`;
const CONTRIBUTE_URL = `${DOCS_BASE_URL}/contribute.html`;
const GITHUB_BASE_URL = 'https://github.com/rotki/rotki/';
const ICONS_BASE_URL =
  'https://raw.githubusercontent.com/rotki/data/main/assets/icons/';

// Cannot be checked with fetch because it always return 400
export const TWITTER_URL = 'https://twitter.com/rotkiapp';

export const externalLinks = {
  premium: `${BASE_URL}products`,
  usageGuide: USAGE_GUIDE_URL,
  usageGuideSection: {
    dockerWarning: `${USAGE_GUIDE_URL}#docker`,
    addingAnExchange: `${USAGE_GUIDE_URL}#adding-an-exchange`
  },
  contribute: CONTRIBUTE_URL,
  contributeSection: {
    coingecko: `${CONTRIBUTE_URL}#get-coingecko-asset-identifier`,
    cryptocompare: `${CONTRIBUTE_URL}#get-cryptocompare-asset-identifier`,
    language: `${CONTRIBUTE_URL}#add-a-new-language-or-translation`
  },
  faq: `${DOCS_BASE_URL}faq.html`,
  changeLog: `${DOCS_BASE_URL}changelog.html`,
  discord: 'https://discord.rotki.com',
  github: GITHUB_BASE_URL,
  githubIssues: `${GITHUB_BASE_URL}issues`,
  githubNewIssue: `${GITHUB_BASE_URL}issues/new/choose`,
  releases: `${GITHUB_BASE_URL}releases`,
  releasesVersion: `${GITHUB_BASE_URL}releases/tag/v$version`,
  etherscan: {
    ethereum: 'https://etherscan.io/register',
    optimism: 'https://optimistic.etherscan.io/register',
    polygonPos: 'https://polygonscan.com/register',
    arbitrum: 'https://arbiscan.io/register',
    base: 'https://basescan.org/register',
    gnosis: 'https://gnosisscan.io/register'
  },
  metamaskDownload: 'https://metamask.io/download/',
  openSeaApiKeyReference:
    'https://docs.opensea.io/reference/api-keys#how-do-i-get-an-api-key',
  logo: {
    about: `${ICONS_BASE_URL}about_logo.png`,
    drawer: `${ICONS_BASE_URL}drawer_logo.png`,
    noData: `${ICONS_BASE_URL}empty_screen_logo.png`
  },
  nftWarning:
    'https://medium.com/@alxlpsc/critical-privacy-vulnerability-getting-exposed-by-metamask-693c63c2ce94'
};

export const externalAssets = {
  logo: {
    about: `${ICONS_BASE_URL}about_logo.png`,
    drawer: `${ICONS_BASE_URL}drawer_logo.png`,
    noData: `${ICONS_BASE_URL}empty_screen_logo.png`
  }
};
