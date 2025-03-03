import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, overload

import requests

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.constants.timing import DAY_IN_SECONDS, YEAR_IN_SECONDS
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKeyOptionalDB
from rotkehlchen.fval import FVal
from rotkehlchen.interfaces import HistoricalPriceOracleWithCoinListInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import ChainID, EvmTokenKind, ExternalService, Price, Timestamp
from rotkehlchen.utils.misc import set_user_agent, timestamp_to_date, ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CoingeckoAssetData(NamedTuple):
    identifier: str
    symbol: str
    name: str
    image_url: str


DELISTED_ASSETS = {
    strethaddress_to_identifier('0x0F72714B35a366285Df85886A2eE174601292A17'),
    'FLUZ',
    'EBCH',
    'GOLOS',
    'NPER',
    strethaddress_to_identifier('0xCA29db4221c111888a7e80b12eAc8a266Da3Ee0d'),
    'ADN',
    'PIX',
    strethaddress_to_identifier('0xdfdc0D82d96F8fd40ca0CFB4A288955bECEc2088'),
    'LKY',
    strethaddress_to_identifier('0xaFBeC4D65BC7b116d85107FD05d912491029Bf46'),
    strethaddress_to_identifier('0x37D40510a2F5Bc98AA7a0f7BF4b3453Bcfb90Ac1'),
    'BITCAR',
    strethaddress_to_identifier('0x499A6B77bc25C26bCf8265E2102B1B3dd1617024'),
    'OLE',
    'ROC',
    'VIN',
    'FIH',
    strethaddress_to_identifier('0x899338b84D25aC505a332aDCE7402d697D947494'),
    'ADH',
    'AUR',
    strethaddress_to_identifier('0x2A05d22DB079BC40C2f77a1d1fF703a56E631cc1'),
    'BYC',
    'DGS',
    strethaddress_to_identifier('0xb3Bd49E28f8F832b8d1E246106991e546c323502'),
    'HST',
    'INS',
    'IPSX',
    'SHP',
    'WDC',
    'BOST',
    'FND',
    'LDC',
    'ORI',
    'RIPT',
    'SGR',
    'LOCUS',
    'REDC',
    'SGN',
    strethaddress_to_identifier('0xD65960FAcb8E4a2dFcb2C2212cb2e44a02e2a57E'),
    strethaddress_to_identifier('0xD9A12Cde03a86E800496469858De8581D3A5353d'),
    'AC',
    strethaddress_to_identifier('0x4C0fBE1BB46612915E7967d2C3213cd4d87257AD'),
    'BITPARK',
    strethaddress_to_identifier('0xB4b1D2C217EC0776584CE08D3DD98F90EDedA44b'),
    'DAN',
    strethaddress_to_identifier('0x89c6c856a6db3e46107163D0cDa7A7FF211BD655'),
    strethaddress_to_identifier('0x07e3c70653548B04f0A75970C1F81B4CBbFB606f'),
    'DROP',
    'ERD',
    'ETBS',
    strethaddress_to_identifier('0x543Ff227F64Aa17eA132Bf9886cAb5DB55DCAddf'),
    'STP',
    'SYNC',
    'TBT',
    'TNT',
    'WIC',
    'XCN',
    strethaddress_to_identifier('0x6368e1E18c4C419DDFC608A0BEd1ccb87b9250fc'),
    'FREC',
    'PTC',
    strethaddress_to_identifier('0x13F1b7FDFbE1fc66676D56483e21B1ecb40b58E2'),
    'J8T',
    'MRK',
    'TTV',
    'ALX',
    'EBC',
    'RCN-2',
    'SKYM',
    strethaddress_to_identifier('0xFA456Cf55250A839088b27EE32A424d7DAcB54Ff'),
    strethaddress_to_identifier('0x12fCd6463E66974cF7bBC24FFC4d40d6bE458283'),
    strethaddress_to_identifier('0x3A1237D38D0Fb94513f85D61679cAd7F38507242'),
    strethaddress_to_identifier('0xf333b2Ace992ac2bBD8798bF57Bc65a06184afBa'),
    strethaddress_to_identifier('0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7'),
    'aLEND',
    'aREP',
    'CRBT',
    'EXC-2',
    strethaddress_to_identifier('0x1da015eA4AD2d3e5586E54b9fB0682Ca3CA8A17a'),
    'CZR',
    'ROCK2',
    'ATMI',
    strethaddress_to_identifier('0x9B11EFcAAA1890f6eE52C6bB7CF8153aC5d74139'),
    strethaddress_to_identifier('0xc88Be04c809856B75E3DfE19eB4dCf0a3B15317a'),
    'CREDO',
    'ETK',
    'FNKOS',
    strethaddress_to_identifier('0x2AEC18c5500f21359CE1BEA5Dc1777344dF4C0Dc'),
    'GIM',
    strethaddress_to_identifier('0xA4eA687A2A7F29cF2dc66B39c68e4411C0D00C49'),
    'KORE',
    'NBAI',
    strethaddress_to_identifier('0xfeDAE5642668f8636A11987Ff386bfd215F942EE'),
    'XEL',
    'ATS',
    'BCY',
    'yDAI+yUSDC+yUSDT+yBUSD',
    'yyDAI+yUSDC+yUSDT+yBUSD',
    'ypaxCrv',
    'crvRenWBTC',
    'crvRenWSBTC',
    'ycrvRenWSBTC',
    'SPRK',
    'VV',
    'DRP',
    'HBZ',
    'TAAS',
    'TRUMPLOSE',
    'TRUMPWIN',
    'ATX-2',
    'SONIQ',
    'TRUST',
    'CDX',
    'CRB',
    'CTX',
    'EGC',
    'ICOS',
    'MTRC',
    'NOX',
    'PHI',
    'RLT',
    'SPIN',
    'VIEW',
    'VRM',
    strethaddress_to_identifier('0xdF1D6405df92d981a2fB3ce68F6A03baC6C0E41F'),
    'SPF',
    'NOBS',
    'DADI',
    strethaddress_to_identifier('0x22dE9912cd3D74953B1cd1F250B825133cC2C1b3'),
    strethaddress_to_identifier('0xAa0bb10CEc1fa372eb3Abc17C933FC6ba863DD9E'),
    strethaddress_to_identifier('0x1BcBc54166F6bA149934870b60506199b6C9dB6D'),
    strethaddress_to_identifier('0x851017523AE205adc9195e7F97D029f4Cfe7794c'),
    strethaddress_to_identifier('0x7f65BE7FAd0c22813e51746E7e8f13a20bAa9411'),
    strethaddress_to_identifier('0xe431a4c5DB8B73c773e06cf2587dA1EB53c41373'),
    strethaddress_to_identifier('0xAef38fBFBF932D1AeF3B808Bc8fBd8Cd8E1f8BC5'),
    strethaddress_to_identifier('0xd341d1680Eeee3255b8C4c75bCCE7EB57f144dAe'),
    'FLO',
    strethaddress_to_identifier('0x06147110022B768BA8F99A8f385df11a151A9cc8'),
    strethaddress_to_identifier('0x27695E09149AdC738A978e9A678F99E4c39e9eb9'),
    'FCN',
    'BITB',
    'SMC',
    'POP',
    'DRM',
    'CRYPT',
    'CPC-2',
    'BSD',
    'BITS',
    strethaddress_to_identifier('0x1695936d6a953df699C38CA21c2140d497C08BD9'),
    strethaddress_to_identifier('0xD6014EA05BDe904448B743833dDF07c3C7837481'),
    strethaddress_to_identifier('0x054C64741dBafDC19784505494029823D89c3b13'),
    strethaddress_to_identifier('0x2ecB13A8c458c379c4d9a7259e202De03c8F3D19'),
    strethaddress_to_identifier('0x4a6058666cf1057eaC3CD3A5a614620547559fc9'),
    strethaddress_to_identifier('0x6F919D67967a97EA36195A2346d9244E60FE0dDB'),
    strethaddress_to_identifier('0x8dB54ca569D3019A2ba126D03C37c44b5eF81EF6'),
    strethaddress_to_identifier('0xb62d18DeA74045E822352CE4B3EE77319DC5ff2F'),
    strethaddress_to_identifier('0x884181554dfA9e578d36379919C05C25dC4a15bB'),
    strethaddress_to_identifier('0xfF18DBc487b4c2E3222d115952bABfDa8BA52F5F'),
    strethaddress_to_identifier('0x957c30aB0426e0C93CD8241E2c60392d08c6aC8e'),
    strethaddress_to_identifier('0x263c618480DBe35C300D8d5EcDA19bbB986AcaeD'),
    strethaddress_to_identifier('0x076C97e1c869072eE22f8c91978C99B4bcB02591'),
    strethaddress_to_identifier('0x8eFFd494eB698cc399AF6231fCcd39E08fd20B15'),
    strethaddress_to_identifier('0x53066cdDBc0099eb6c96785d9b3DF2AAeEDE5DA3'),
    strethaddress_to_identifier('0x9214eC02CB71CbA0ADA6896b8dA260736a67ab10'),
    strethaddress_to_identifier('0xabC1280A0187a2020cC675437aed400185F86Db6'),
    strethaddress_to_identifier('0x23b75Bc7AaF28e2d6628C3f424B3882F8f072a3c'),
    'BTCS',
    strethaddress_to_identifier('0x491C9A23DB85623EEd455a8EfDd6AbA9b911C5dF'),
    strethaddress_to_identifier('0x8aA33A7899FCC8eA5fBe6A608A109c3893A1B8b2'),
    'ARB-2',
    'BAY',
    'UNITY',
    strethaddress_to_identifier('0x8d80de8A78198396329dfA769aD54d24bF90E7aa'),
    strethaddress_to_identifier('0x5bEaBAEBB3146685Dd74176f68a0721F91297D37'),
    strethaddress_to_identifier('0x82f4dED9Cec9B5750FBFf5C2185AEe35AfC16587'),
    strethaddress_to_identifier('0x74CEDa77281b339142A36817Fa5F9E29412bAb85'),
    strethaddress_to_identifier('0xDDe12a12A6f67156e0DA672be05c374e1B0a3e57'),
    strethaddress_to_identifier('0x2bDC0D42996017fCe214b21607a515DA41A9E0C5'),
    strethaddress_to_identifier('0x1c79ab32C66aCAa1e9E81952B8AAa581B43e54E7'),
    strethaddress_to_identifier('0xD3C00772B24D997A812249ca637a921e81357701'),
    'DCT',
    'NOTE',
    'SLR',
    'SXC',
    strethaddress_to_identifier('0x6fFF3806Bbac52A20e0d79BC538d527f6a22c96b'),
    strethaddress_to_identifier('0x78B7FADA55A64dD895D8c8c35779DD8b67fA8a05'),
    strethaddress_to_identifier('0x4D8fc1453a0F359e99c9675954e656D80d996FbF'),
    strethaddress_to_identifier('0xFAd572db566E5234AC9Fc3d570c4EdC0050eAA92'),
    strethaddress_to_identifier('0xBB49A51Ee5a66ca3a8CbE529379bA44Ba67E6771'),
    strethaddress_to_identifier('0x2e071D2966Aa7D8dECB1005885bA1977D6038A65'),
    strethaddress_to_identifier('0x6589fe1271A0F29346796C6bAf0cdF619e25e58e'),
    strethaddress_to_identifier('0xDd6C68bb32462e01705011a4e2Ad1a60740f217F'),
    strethaddress_to_identifier('0x13C2fab6354d3790D8ece4f0f1a3280b4A25aD96'),
    strethaddress_to_identifier('0x5979F50f1D4c08f9A53863C2f39A7B0492C38d0f'),
    strethaddress_to_identifier('0xaE73B38d1c9A8b274127ec30160a4927C4d71824'),
    strethaddress_to_identifier('0x12e51E77DAAA58aA0E9247db7510Ea4B46F9bEAd'),
    strethaddress_to_identifier('0xcbb20D755ABAD34cb4a9b5fF6Dd081C76769f62e'),
    strethaddress_to_identifier('0xB4EaF48bD7f72356e1019C157e91b81A1C541073'),
    strethaddress_to_identifier('0x2a093BcF0C98Ef744Bb6F69D74f2F85605324290'),
    strethaddress_to_identifier('0x7B22938ca841aA392C93dBB7f4c42178E3d65E88'),
    strethaddress_to_identifier('0x47bc01597798DCD7506DCCA36ac4302fc93a8cFb'),
    strethaddress_to_identifier('0x6aEDbF8dFF31437220dF351950Ba2a3362168d1b'),
    strethaddress_to_identifier('0x31f3D9D1BeCE0c033fF78fA6DA60a6048F3E13c5'),
    strethaddress_to_identifier('0x00c4B398500645eb5dA00a1a379a88B11683ba01'),
    strethaddress_to_identifier('0x5B2e4a700dfBc560061e957edec8F6EeEb74a320'),
    strethaddress_to_identifier('0x68AA3F232dA9bdC2343465545794ef3eEa5209BD'),
    strethaddress_to_identifier('0x905E337c6c8645263D3521205Aa37bf4d034e745'),
    strethaddress_to_identifier('0xE477292f1B3268687A29376116B0ED27A9c76170'),
    strethaddress_to_identifier('0x9fBFed658919A896B5Dc7b00456Ce22D780f9B65'),
    strethaddress_to_identifier('0xAFe60511341a37488de25Bef351952562E31fCc1'),
    strethaddress_to_identifier('0x3c4bEa627039F0B7e7d21E34bB9C9FE962977518'),
    strethaddress_to_identifier('0x48FF53777F747cFB694101222a944dE070c15D36'),
    strethaddress_to_identifier('0xe2DA716381d7E0032CECaA5046b34223fC3f218D'),
    strethaddress_to_identifier('0x2fdF40C484b1BD6F1c214ACAC737FEDc8b03E5a8'),
    strethaddress_to_identifier('0x88665A7556E1B3C939D6661248116886845249a8'),
    'XVC',
    'MCN',
    strethaddress_to_identifier('0xac2e58A06E6265F1Cf5084EE58da68e5d75b49CA'),
    strethaddress_to_identifier('0x50f09629d0afDF40398a3F317cc676cA9132055c'),
    strethaddress_to_identifier('0xd234BF2410a0009dF9c3C63b610c09738f18ccD7'),
    strethaddress_to_identifier('0xb2F7EB1f2c37645bE61d73953035360e768D81E6'),
    strethaddress_to_identifier('0x554C20B7c486beeE439277b4540A434566dC4C02'),
    strethaddress_to_identifier('0xCc80C051057B774cD75067Dc48f8987C4Eb97A5e'),
    strethaddress_to_identifier('0x4D807509aECe24C0fa5A102b6a3B059Ec6E14392'),
    strethaddress_to_identifier('0xcCeD5B8288086BE8c38E23567e684C3740be4D48'),
    strethaddress_to_identifier('0x6Ba460AB75Cd2c56343b3517ffeBA60748654D26'),
    strethaddress_to_identifier('0x92E78dAe1315067a8819EFD6dCA432de9DCdE2e9'),
    strethaddress_to_identifier('0xC76FB75950536d98FA62ea968E1D6B45ffea2A55'),
    'FAIR',
    'BUX',
    strethaddress_to_identifier('0x03C780cD554598592B97b7256dDAad759945b125'),
    strethaddress_to_identifier('0x04F2E7221fdb1B52A68169B25793E51478fF0329'),
    strethaddress_to_identifier('0x17B26400621695c2D8C2D8869f6259E82D7544c4'),
    strethaddress_to_identifier('0x613Fa2A6e6DAA70c659060E86bA1443D2679c9D7'),
    strethaddress_to_identifier('0x4689a4e169eB39cC9078C0940e21ff1Aa8A39B9C'),
    strethaddress_to_identifier('0x3d1BA9be9f66B8ee101911bC36D3fB562eaC2244'),
    strethaddress_to_identifier('0x3d1BA9be9f66B8ee101911bC36D3fB562eaC2244'),
    strethaddress_to_identifier('0xecd570bBf74761b960Fa04Cc10fe2c4e86FfDA36'),
    strethaddress_to_identifier('0xf1a91C7d44768070F711c68f33A7CA25c8D30268'),
    strethaddress_to_identifier('0xDCEcf0664C33321CECA2effcE701E710A2D28A3F'),
    'BBR',
    'CNL',
    'DOPE',
    'ECC',
    'SDT',
    'TEDDY',
    'ICA',
    'BAG',
    'MCT',
    'LOL',
    strethaddress_to_identifier('0xE081b71Ed098FBe1108EA48e235b74F122272E68'),
    'eip155:56/erc20:0xDCEcf0664C33321CECA2effcE701E710A2D28A3F',
    strethaddress_to_identifier('0xDf6Ef343350780BF8C3410BF062e0C015B1DD671'),
    strethaddress_to_identifier('0x24dDFf6D8B8a42d835af3b440De91f3386554Aa4'),
    strethaddress_to_identifier('0xD29F0b5b3F50b07Fe9a9511F7d86F4f4bAc3f8c4'),
    strethaddress_to_identifier('0xf05a9382A4C3F29E2784502754293D88b835109C'),
    strethaddress_to_identifier('0xf3C092cA8CD6D3d4ca004Dc1d0f1fe8CcAB53599'),
    strethaddress_to_identifier('0x43f11c02439e2736800433b4594994Bd43Cd066D'),
    'TOR',
    strethaddress_to_identifier('0x5c6D51ecBA4D8E4F20373e3ce96a62342B125D6d'),
    strethaddress_to_identifier('0xfec0cF7fE078a500abf15F1284958F22049c2C7e'),
    strethaddress_to_identifier('0xe1A178B681BD05964d3e3Ed33AE731577d9d96dD'),
    strethaddress_to_identifier('0xfD62247943F94C3910A4922af2C62C2D3fAC2a8f'),
    strethaddress_to_identifier('0x68eb95Dc9934E19B86687A10DF8e364423240E94'),
    strethaddress_to_identifier('0x1d462414fe14cf489c7A21CaC78509f4bF8CD7c0'),
    strethaddress_to_identifier('0x0223fc70574214F65813fE336D870Ac47E147fAe'),
    strethaddress_to_identifier('0x151202C9c18e495656f372281F493EB7698961D5'),
    strethaddress_to_identifier('0xDE1E0AE6101b46520cF66fDC0B1059c5cC3d106c'),
    strethaddress_to_identifier('0x1CCAA0F2a7210d76E1fDec740d5F323E2E1b1672'),
    strethaddress_to_identifier('0x1829aA045E21E0D59580024A951DB48096e01782'),
    strethaddress_to_identifier('0x6DD4e4Aad29A40eDd6A409b9c1625186C9855b4D'),
    strethaddress_to_identifier('0x423b5F62b328D0D6D44870F4Eee316befA0b2dF5'),
    strethaddress_to_identifier('0x5E6b6d9aBAd9093fdc861Ea1600eBa1b355Cd940'),
    strethaddress_to_identifier('0x4Cd988AfBad37289BAAf53C13e98E2BD46aAEa8c'),
    strethaddress_to_identifier('0x4618519de4C304F3444ffa7f812dddC2971cc688'),
    strethaddress_to_identifier('0x7CC62d8E80Be9bEa3947F3443aD136f50f75b505'),
    strethaddress_to_identifier('0x1966d718A565566e8E202792658D7b5Ff4ECe469'),
    strethaddress_to_identifier('0x4355fC160f74328f9b383dF2EC589bB3dFd82Ba0'),
    strethaddress_to_identifier('0xc42209aCcC14029c1012fB5680D95fBd6036E2a0'),
    strethaddress_to_identifier('0x9972A0F24194447E73a7e8b6CD26a52e02DDfAD5'),
    strethaddress_to_identifier('0x3209f98BeBF0149B769ce26D71F7aEA8E435EfEa'),
    strethaddress_to_identifier('0x8B40761142B9aa6dc8964e61D0585995425C3D94'),
    strethaddress_to_identifier('0x9389434852b94bbaD4c8AfEd5B7BDBc5Ff0c2275'),
    strethaddress_to_identifier('0x445f51299Ef3307dBD75036dd896565F5B4BF7A5'),
    strethaddress_to_identifier('0x5c543e7AE0A1104f78406C340E9C64FD9fCE5170'),
    strethaddress_to_identifier('0xb4bebD34f6DaaFd808f73De0d10235a92Fbb6c3D'),
    strethaddress_to_identifier('0x7C81542ED859A2061538FEE22B6544a235B9557D'),
    strethaddress_to_identifier('0xbf0f3cCB8fA385A287106FbA22e6BB722F94d686'),
    strethaddress_to_identifier('0x19D3364A399d251E894aC732651be8B0E4e85001'),
    strethaddress_to_identifier('0xB98Df7163E61bf053564bde010985f67279BBCEC'),
    strethaddress_to_identifier('0xBFa4D8AA6d8a379aBFe7793399D3DdaCC5bBECBB'),
    strethaddress_to_identifier('0xEd279fDD11cA84bEef15AF5D39BB4d4bEE23F0cA'),
    strethaddress_to_identifier('0x63739d137EEfAB1001245A8Bd1F3895ef3e186E7'),
    strethaddress_to_identifier('0xdA816459F1AB5631232FE5e97a05BBBb94970c95'),
    evm_address_to_identifier(address='0x007EA5C0Ea75a8DF45D288a4debdD5bb633F9e56', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x3f515f0a8e93F2E2f891ceeB3Db4e62e202d7110', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    'BBK-2',
    'IFC',
    'MEC',
    'PAI',
    'PPC',
    'HOLY',
    'COIN',
    'WNDR',
    'DESO',
    strethaddress_to_identifier('0x1A0F2aB46EC630F9FD638029027b552aFA64b94c'),
    strethaddress_to_identifier('0x84F7c44B6Fed1080f647E354D552595be2Cc602F'),
    strethaddress_to_identifier('0x923108a439C4e8C2315c4f6521E5cE95B44e9B4c'),
    strethaddress_to_identifier('0x4270bb238f6DD8B1c3ca01f96CA65b2647c06D3C'),
    strethaddress_to_identifier('0x60c68a87bE1E8a84144b543AAcfA77199cd3d024'),
    strethaddress_to_identifier('0xB70835D7822eBB9426B56543E391846C107bd32C'),
    strethaddress_to_identifier('0x9AF839687F6C94542ac5ece2e317dAAE355493A1'),
    strethaddress_to_identifier('0x23Ccc43365D9dD3882eab88F43d515208f832430'),
    strethaddress_to_identifier('0x5d48F293BaED247A2D0189058bA37aa238bD4725'),
    strethaddress_to_identifier('0xF88951D7B676798705fd3a362ba5B1DBca2B233b'),
    strethaddress_to_identifier('0x4824A7b64E3966B0133f4f4FFB1b9D6bEb75FFF7'),
    strethaddress_to_identifier('0x840fe75ABfaDc0F2d54037829571B2782e919ce4'),
    strethaddress_to_identifier('0x23Ccc43365D9dD3882eab88F43d515208f832430'),
    strethaddress_to_identifier('0x23Ccc43365D9dD3882eab88F43d515208f832430'),
    strethaddress_to_identifier('0x824a50dF33AC1B41Afc52f4194E2e8356C17C3aC'),
    evm_address_to_identifier(address='0x6cd871fb811224aa23B6bF1646177CdFe5106416', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x7786B28826e2DDA4dBe344bE66A0bFbfF3d3362f', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x11C0c93035d1302083eB09841042cFa582839A8C', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    strethaddress_to_identifier('0xC12D1c73eE7DC3615BA4e37E4ABFdbDDFA38907E'),
    'SILK',
    'CRT',
    'EAC',
    strethaddress_to_identifier('0xb8919522331C59f5C16bDfAA6A121a6E03A91F62'),
    strethaddress_to_identifier('0x4289c043A12392F1027307fB58272D8EBd853912'),
    strethaddress_to_identifier('0x016ee7373248a80BDe1fD6bAA001311d233b3CFa'),
    strethaddress_to_identifier('0x1234567461d3f8Db7496581774Bd869C83D51c93'),
    strethaddress_to_identifier('0x06AF07097C9Eeb7fD685c692751D5C66dB49c215'),
    strethaddress_to_identifier('0xF41e5Fbc2F6Aac200Dd8619E121CE1f05D150077'),
    strethaddress_to_identifier('0x672a1AD4f667FB18A333Af13667aa0Af1F5b5bDD'),
    strethaddress_to_identifier('0x5adc961D6AC3f7062D2eA45FEFB8D8167d44b190'),
    strethaddress_to_identifier('0x47b28F365Bf4CB38DB4B6356864BDE7bc4B35129'),
    strethaddress_to_identifier('0x687174f8C49ceb7729D925C3A961507ea4Ac7b28'),
    strethaddress_to_identifier('0x13119E34E140097a507B07a5564bDe1bC375D9e6'),
    strethaddress_to_identifier('0x123aB195DD38B1b40510d467a6a359b201af056f'),
    strethaddress_to_identifier('0x6BEB418Fc6E1958204aC8baddCf109B8E9694966'),
    strethaddress_to_identifier('0xb0dFd28d3CF7A5897C694904Ace292539242f858'),
    strethaddress_to_identifier('0x5dbe296F97B23C4A6AA6183D73e574D02bA5c719'),
    strethaddress_to_identifier('0x01F2AcF2914860331C1Cb1a9AcecDa7475e06Af8'),
    strethaddress_to_identifier('0x5D4d57cd06Fa7fe99e26fdc481b468f77f05073C'),
    strethaddress_to_identifier('0x8064d9Ae6cDf087b1bcd5BDf3531bD5d8C537a68'),
    strethaddress_to_identifier('0x832904863978b94802123106e6eB491BDF0Df928'),
    strethaddress_to_identifier('0xBb1f24C0c1554b9990222f036b0AaD6Ee4CAec29'),
    strethaddress_to_identifier('0x20F7A3DdF244dc9299975b4Da1C39F8D5D75f05A'),
    strethaddress_to_identifier('0xF70a642bD387F94380fFb90451C2c81d4Eb82CBc'),
    strethaddress_to_identifier('0xBAE235823D7255D9D48635cEd4735227244Cd583'),
    strethaddress_to_identifier('0xE4E822C0d5b329E8BB637972467d2E313824eFA0'),
    strethaddress_to_identifier('0x6bC1F3A1ae56231DbB64d3E82E070857EAe86045'),
    strethaddress_to_identifier('0x7025baB2EC90410de37F488d1298204cd4D6b29d'),
    strethaddress_to_identifier('0x37941b3Fdb2bD332e667D452a58Be01bcacb923e'),
    strethaddress_to_identifier('0xEd025A9Fe4b30bcd68460BCA42583090c2266468'),
    strethaddress_to_identifier('0xeEd4d7316a04ee59de3d301A384262FFbDbd589a'),
    evm_address_to_identifier(address='0xF301C8435D4dFA51641f71B0615aDD794b52c8E9', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    strethaddress_to_identifier('0x18084fbA666a33d37592fA2633fD49a74DD93a88'),
    'FB',
    'ROAD',
    'SPD-2',
    'PLA',
    'MER',
    'DYN',
    'CMT',
    'BLU',
    'ARC',
    evm_address_to_identifier(address='0x1180C484f55024C5Ce1765101f4efaC1e7A3F6d4', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x37941b3Fdb2bD332e667D452a58Be01bcacb923e', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xA68Dd8cB83097765263AdAD881Af6eeD479c4a33', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x34364BEe11607b1963d66BCA665FDE93fCA666a8', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xa456b515303B2Ce344E9d2601f91270f8c2Fea5E', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x82b0E50478eeaFde392D45D1259Ed1071B6fDa81', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x4672bAD527107471cB5067a887f4656D585a8A31', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xf263292e14d9D8ECd55B58dAD1F1dF825a874b7c', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x0AF44e2784637218dD1D32A322D44e603A8f0c6A', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x85ca6710D0F1D511d130f6935eDDA88ACBD921bD', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x6888a16eA9792c15A4DCF2f6C623D055c8eDe792', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x1F3f9D3068568F8040775be2e8C03C103C61f3aF', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x622dFfCc4e83C64ba959530A5a5580687a57581b', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x2e98A6804E4b6c832ED0ca876a943abD3400b224', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x539EfE69bCDd21a83eFD9122571a64CC25e0282b', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x26DB5439F651CAF491A87d48799dA81F191bDB6b', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xb1c1Cb8C7c1992dba24e628bF7d38E71daD46aeB', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xd780Ae2Bf04cD96E577D3D014762f831d97129d0', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x68909e586eeAC8F47315e84B4c9788DD54Ef65Bb', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xeC46f8207D766012454c408De210BCBc2243E71c', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xEee2d00Eb7DEB8Dd6924187f5AA3496B7d06E62A', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x58a4884182d9E835597f405e5F258290E46ae7C2', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x126c121f99e1E211dF2e5f8De2d96Fa36647c855', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xE38B72d6595FD3885d1D2F770aa23E94757F91a1', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x60EF10EDfF6D600cD91caeCA04caED2a2e605Fe5', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xfC1Cb4920dC1110fD61AfaB75Cf085C1f871b8C6', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xAE6e3540E97b0b9EA8797B157B510e133afb6282', chain_id=ChainID.ARBITRUM_ONE, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x6bfd576220e8444CA4Cc5f89Efbd7f02a4C94C16', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    'TFC',
    'DON',
    'NUT',
    evm_address_to_identifier(address='0x06B884e60794Ce02AafAb13791B59A2e6A07442f', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x37E8789bB9996CaC9156cD5F5Fd32599E6b91289', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xE4f726Adc8e89C6a6017F01eadA77865dB22dA14', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x95aA5d2DbD3c16ee3fdea82D5C6EC3E38CE3314f', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x114f1388fAB456c4bA31B1850b244Eedcd024136', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xDa007777D86AC6d989cC9f79A73261b3fC5e0DA0', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xAC8E13ecC30Da7Ff04b842f21A62a1fb0f10eBd5', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x0000000000004946c0e9F43F4Dee607b0eF1fA1c', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x670f9D9a26D3D42030794ff035d35a67AA092ead', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x1c7E83f8C581a967940DBfa7984744646AE46b29', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x75C9bC761d88f70156DAf83aa010E84680baF131', chain_id=ChainID.ARBITRUM_ONE, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x557f20CE25b41640ADe4a3085d42d7e626d7965A', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xc56c2b7e71B54d38Aab6d52E94a04Cbfa8F604fA', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x628eBC64A38269E031AFBDd3C5BA857483B5d048', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0x24086EAb82DBDaa4771d0A5D66B0D810458b0E86', chain_id=ChainID.BINANCE_SC, token_type=EvmTokenKind.ERC20),  # noqa: E501
    evm_address_to_identifier(address='0xCB5A05beF3257613E984C17DbcF039952B6d883F', chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20),  # noqa: E501
}

COINGECKO_SIMPLE_VS_CURRENCIES = {
    'btc',
    'eth',
    'ltc',
    'bch',
    'bnb',
    'eos',
    'xrp',
    'xlm',
    'link',
    'dot',
    'yfi',
    'usd',
    'aed',
    'ars',
    'aud',
    'bdt',
    'bhd',
    'bmd',
    'brl',
    'cad',
    'chf',
    'clp',
    'cny',
    'czk',
    'dkk',
    'eur',
    'gbp',
    'hkd',
    'huf',
    'idr',
    'ils',
    'inr',
    'jpy',
    'krw',
    'kwd',
    'lkr',
    'mmk',
    'mxn',
    'myr',
    'nok',
    'nzd',
    'php',
    'pkr',
    'pln',
    'rub',
    'sar',
    'sek',
    'sgd',
    'thb',
    'try',
    'twd',
    'uah',
    'vef',
    'vnd',
    'zar',
    'xdr',
    'xag',
    'xau',
}


class Coingecko(
        ExternalServiceWithApiKeyOptionalDB,
        HistoricalPriceOracleWithCoinListInterface,
        PenalizablePriceOracleMixin,
):

    def __init__(self, database: 'DBHandler | None') -> None:
        ExternalServiceWithApiKeyOptionalDB.__init__(self, database=database, service_name=ExternalService.COINGECKO)  # noqa: E501
        HistoricalPriceOracleWithCoinListInterface.__init__(self, oracle_name='coingecko')
        PenalizablePriceOracleMixin.__init__(self)
        self.session = create_session()
        set_user_agent(self.session)
        self.db: DBHandler | None  # type: ignore  # "solve" the self.db discrepancy

    @overload
    def _query(
            self,
            module: Literal['coins/list'],
            subpath: str | None = None,
            options: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    @overload
    def _query(
            self,
            module: Literal['coins', 'simple/price'],
            subpath: str | None = None,
            options: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        ...

    def _query(
            self,
            module: str,
            subpath: str | None = None,
            options: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Performs a coingecko query

        May raise:
        - RemoteError if there is a problem querying coingecko
        """
        if (api_key := self._get_api_key()) is not None:
            base_url = 'https://pro-api.coingecko.com/api/v3'
        else:
            base_url = 'https://api.coingecko.com/api/v3'

        if options is None:
            options = {}
        url = f'{base_url}/{module}/{subpath or ""}'
        if api_key:
            self.session.headers.update({'x-cg-pro-api-key': api_key})
        else:
            self.session.headers.pop('x-cg-pro-api-key', None)

        log.debug(f'Querying coingecko: {url=} with {options=}')
        try:
            response = self.session.get(
                url=url,
                params=options,
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            self.penalty_info.note_failure_or_penalize()
            raise RemoteError(f'Coingecko API request failed due to {e!s}') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            self.last_rate_limit = ts_now()
            msg = f'Got rate limited by coingecko querying {url}'
            log.warning(msg)
            raise RemoteError(message=msg, error_code=HTTPStatus.TOO_MANY_REQUESTS)

        if response.status_code != 200:
            msg = (
                f'Coingecko API request {response.url} failed with HTTP status '
                f'code: {response.status_code}'
            )
            raise RemoteError(msg)

        try:
            decoded_json = json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            msg = f'Invalid JSON in Coingecko response. {e}'
            raise RemoteError(msg) from e

        return decoded_json

    def asset_data(self, asset_coingecko_id: str) -> CoingeckoAssetData:
        """
        Query coingecko to retrieve the asset information related to the provided coingecko id
        May raise:
        - UnsupportedAsset() if the asset is not supported by coingecko
        - RemoteError if there is a problem querying coingecko
        """
        options = {
            # Include all localized languages in response (true/false) [default: true]
            'localization': 'false',
            # Include tickers data (true/false) [default: true]
            'tickers': 'false',
            # Include market_data (true/false) [default: true]
            'market_data': 'false',
            # Include communitydata (true/false) [default: true]
            'community_data': 'false',
            # Include developer data (true/false) [default: true]
            'developer_data': 'false',
            # Include sparkline 7 days data (eg. true, false) [default: false]
            'sparkline': 'false',
        }
        data = self._query(
            module='coins',
            subpath=asset_coingecko_id,
            options=options,
        )

        # https://github.com/PyCQA/pylint/issues/4739
        try:
            parsed_data = CoingeckoAssetData(
                identifier=asset_coingecko_id,
                symbol=data['symbol'],
                name=data['name'],
                image_url=data['image']['small'],
            )
        except KeyError as e:
            raise RemoteError(
                f'Missing expected key entry {e} in coingecko coin data response',
            ) from e

        return parsed_data

    def all_coins(self) -> dict[str, dict[str, Any]]:
        """Returns all coingecko assets

        May raise:
        - RemoteError if there is an error with reaching coingecko
        """
        if (data := self.maybe_get_cached_coinlist(considered_recent_secs=DAY_IN_SECONDS)) is None:
            data = {}
            response = self._query(module='coins/list')
            for entry in response:
                if entry['id'] in data:
                    log.warning(
                        f'Found duplicate coingecko identifier {entry["id"]} when querying '
                        f'the list of coingecko assets. Ignoring...',
                    )
                    continue

                identifier = entry.pop('id')
                data[identifier] = entry

            self.cache_coinlist(data)

        return data

    @staticmethod
    def check_vs_currencies(
            to_asset: AssetWithOracles,
            location: str,
            from_asset: AssetWithOracles | None = None,
    ) -> str | None:
        vs_currency = to_asset.identifier.lower()
        if vs_currency not in COINGECKO_SIMPLE_VS_CURRENCIES:
            log.warning(
                f'Tried to query coingecko {location} from '
                f"{from_asset.identifier if from_asset is not None else 'multiple assets'} "
                f'to {to_asset.identifier}. But to_asset is not supported',
            )
            return None

        return vs_currency

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """Wrapper for query_multiple_current_prices when only querying a single price.
        Returns the asset price or ZERO_PRICE if no price is found.
        """
        return self.query_multiple_current_prices(
            from_assets=[from_asset],
            to_asset=to_asset,
        ).get(from_asset, ZERO_PRICE)

    def query_multiple_current_prices(
            self,
            from_assets: list[AssetWithOracles],
            to_asset: AssetWithOracles,
    ) -> dict[AssetWithOracles, Price]:
        """Query simple prices for from_assets to to_asset from coingecko.

        Uses the simple/price endpoint of coingecko. If to_asset is not part of the
        coingecko simple vs currencies querying is skipped and all assets are returned as failed.

        Returns a dict mapping assets to prices found. Assets for which a price was not found
        are not included in the dict.

        May raise:
        - RemoteError if there is a problem querying coingecko
        """
        vs_currency = Coingecko.check_vs_currencies(
            to_asset=to_asset,
            location='simple price',
        )
        if not vs_currency:
            return {}

        coingecko_ids_to_assets: dict[str, AssetWithOracles] = {}
        for from_asset in from_assets:
            try:
                coingecko_ids_to_assets[from_asset.to_coingecko()] = from_asset
            except UnsupportedAsset:
                log.debug(
                    f'Tried to query coingecko simple price from {from_asset.identifier} '
                    f'to {to_asset.identifier}. But from_asset is not supported in coingecko',
                )

        if len(coingecko_ids_to_assets) == 0:
            return {}

        result = self._query(
            module='simple/price',
            options={
                'ids': ','.join(coingecko_ids_to_assets.keys()),
                'vs_currencies': vs_currency,
            })

        prices: dict[AssetWithOracles, Price] = {}
        for coingecko_id, from_asset in coingecko_ids_to_assets.items():
            try:
                prices[from_asset] = Price(deserialize_fval(
                    value=result[coingecko_id][vs_currency],
                    name=f'{from_asset} price',
                    location='coingecko price query',
                ))
            except KeyError as e:
                log.warning(
                    f'Queried coingecko simple price from {from_asset.identifier} '
                    f'to {to_asset.identifier}. But got key error for {e!s} when '
                    f'processing the result.',
                )

        return prices

    def can_query_history(
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,
            timestamp: Timestamp,
            seconds: int | None = None,
    ) -> bool:
        """Apart from penalization, for coingecko if there is no paid API key then it won't
        allow you to query further than a year in history. So let's save ourselves network calls"""
        if self.api_key is None and ts_now() - timestamp > YEAR_IN_SECONDS:
            return False

        return not self.is_penalized()

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """
        May raise:
        - PriceQueryUnsupportedAsset if either from_asset or to_asset are not supported
        """
        try:
            from_asset = from_asset.resolve_to_asset_with_oracles()
            to_asset = to_asset.resolve_to_asset_with_oracles()
        except UnknownAsset as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e
        vs_currency = Coingecko.check_vs_currencies(
            from_asset=from_asset,
            to_asset=to_asset,
            location='historical price',
        )
        if not vs_currency:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )

        try:
            from_coingecko_id = from_asset.to_coingecko()
        except UnsupportedAsset as e:
            log.warning(
                f'Tried to query coingecko historical price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But from_asset is not supported in coingecko',
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            ) from e

        date = timestamp_to_date(timestamp, formatstr='%d-%m-%Y')
        result = self._query(
            module='coins',
            subpath=f'{from_coingecko_id}/history',
            options={
                'date': date,
                'localization': 'false',
            },
        )
        # https://github.com/PyCQA/pylint/issues/4739
        try:
            price = Price(FVal(result['market_data']['current_price'][vs_currency]))
        except KeyError as e:
            log.warning(
                f'Queried coingecko historical price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But got key error for {e!s} when '
                f'processing the result.',
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            ) from e

        return price
