import { TransactionEventProtocol } from '@/types/transaction';
import { type ActionDataEntry } from '@/types/action';

export const transactionEventProtocolData = computed<ActionDataEntry[]>(() => [
  {
    identifier: TransactionEventProtocol['1INCH'],
    label: '1inch',
    image: './assets/images/defi/1inch.svg',
    matcher: (identifier: string): boolean =>
      identifier.toLowerCase().startsWith('1inch')
  },
  {
    identifier: TransactionEventProtocol.AAVE,
    label: 'Aave',
    image: './assets/images/defi/aave.svg',
    matcher: (identifier: string): boolean =>
      identifier.toLowerCase().startsWith('aave')
  },
  {
    identifier: TransactionEventProtocol.BADGER,
    label: 'badger',
    image: './assets/images/defi/badger.png'
  },
  {
    identifier: TransactionEventProtocol.COMPOUND,
    label: 'Compound',
    image: './assets/images/defi/compound.svg'
  },
  {
    identifier: TransactionEventProtocol.CONVEX,
    label: 'Convex',
    image: './assets/images/defi/convex.jpeg'
  },
  {
    identifier: TransactionEventProtocol.CURVE,
    label: 'Curve.fi',
    image: './assets/images/defi/curve.svg'
  },
  {
    identifier: TransactionEventProtocol.DXDAO,
    label: 'dxdao',
    image: './assets/images/defi/dxdao.svg',
    matcher: (identifier: string): boolean =>
      identifier.toLowerCase().startsWith('dxdao')
  },
  {
    identifier: TransactionEventProtocol.ELEMENT_FINANCE,
    label: 'Element Finance',
    image: './assets/images/defi/element_finance.png'
  },
  {
    identifier: TransactionEventProtocol.ENS,
    label: 'ens',
    image: './assets/images/airdrops/ens.svg'
  },
  {
    identifier: TransactionEventProtocol.ETH2,
    label: 'ETH2',
    image: './assets/images/modules/eth.svg'
  },
  {
    identifier: TransactionEventProtocol.FRAX,
    label: 'FRAX',
    image: './assets/images/defi/frax.png'
  },
  {
    identifier: TransactionEventProtocol.GITCOIN,
    label: 'Gitcoin',
    image: './assets/images/gitcoin.svg'
  },
  {
    identifier: TransactionEventProtocol.GNOSIS_CHAIN,
    label: 'Gnosis Chain',
    image: './assets/images/chains/gnosis.svg'
  },
  {
    identifier: TransactionEventProtocol.HOP_PROTOCOL,
    label: 'Hop Protocol',
    image: './assets/images/hop_protocol.png'
  },
  {
    identifier: TransactionEventProtocol.KRAKEN,
    label: 'Kraken',
    image: './assets/images/exchanges/kraken.svg'
  },
  {
    identifier: TransactionEventProtocol.KYBER_LEGACY,
    label: 'Kyber Legacy',
    image: './assets/images/defi/kyber.svg'
  },
  {
    identifier: TransactionEventProtocol.LIQUITY,
    label: 'Liquity',
    image: './assets/images/defi/liquity.svg'
  },
  {
    identifier: TransactionEventProtocol.MAKERDAO,
    label: 'Makerdao',
    image: './assets/images/defi/makerdao.svg',
    matcher: (identifier: string): boolean =>
      identifier.toLowerCase().startsWith('makerdao')
  },
  {
    identifier: TransactionEventProtocol.OPTIMISM,
    label: 'Optimism',
    image: './assets/images/chains/optimism.svg'
  },
  {
    identifier: TransactionEventProtocol.PICKLE,
    label: 'Pickle Finance',
    image: './assets/images/modules/pickle.svg'
  },
  {
    identifier: TransactionEventProtocol.SHAPESHIFT,
    label: 'Shapeshift',
    image: './assets/images/shapeshift.svg'
  },
  {
    identifier: TransactionEventProtocol.SUSHISWAP,
    label: 'Sushiswap',
    image: './assets/images/defi/sushi.png',
    matcher: (identifier: string): boolean =>
      identifier.toLowerCase().startsWith('sushiswap')
  },
  {
    identifier: TransactionEventProtocol.UNISWAP,
    label: 'Uniswap',
    image: './assets/images/defi/uniswap.svg',
    matcher: (identifier: string): boolean =>
      identifier.toLowerCase().startsWith('uniswap')
  },
  {
    identifier: TransactionEventProtocol.VOTIUM,
    label: 'Votium',
    image: './assets/images/defi/votium.png'
  },
  {
    identifier: TransactionEventProtocol.WETH,
    label: 'WETH',
    image: './assets/images/defi/weth.svg'
  },
  {
    identifier: TransactionEventProtocol.XDAI,
    label: 'Aave',
    image: './assets/images/defi/xdai.png'
  },
  {
    identifier: TransactionEventProtocol.YEARN,
    label: 'Yearn',
    image: './assets/images/defi/yearn_vaults.svg'
  },
  {
    identifier: TransactionEventProtocol.ZKSYNC,
    label: 'zkSync',
    image: './assets/images/zksync.jpg'
  }
]);
