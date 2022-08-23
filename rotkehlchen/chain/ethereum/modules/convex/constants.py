from rotkehlchen.chain.ethereum.types import string_to_evm_address


CPT_CONVEX = 'convex'

BOOSTER = string_to_evm_address('0xF403C135812408BFbE8713b5A23a04b3D48AAE31')
CVX_LOCKER = string_to_evm_address('0xD18140b4B819b895A3dba5442F959fA44994AF50')
CVX_LOCKER_V2 = string_to_evm_address('0x72a19342e8F1838460eBFCCEf09F6585e32db86E')
CVX_REWARDS = string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332')
CVXCRV_REWARDS = string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e')

CVX_WITHDRAW_TOPIC = b'p\x84\xf5Gf\x18\xd8\xe6\x0b\x11\xef\r}?\x06\x91FU\xad\xb8y>(\xff\x7f\x01\x8dLv\xd5\x05\xd5'  # noqa: E501
CVXCRV_REWARD_PAID_TOPIC = b'\xe2@6@\xbah\xfe\xd3\xa2\xf8\x8buWU\x1d\x19\x93\xf8K\x99\xbb\x10\xff\x83?\x0c\xf8\xdb\x0c^\x04\x86'  # noqa: E501
CVXCRV_WITHDRAWAL_TOPIC = b'p\x84\xf5Gf\x18\xd8\xe6\x0b\x11\xef\r}?\x06\x91FU\xad\xb8y>(\xff\x7f\x01\x8dLv\xd5\x05\xd5'  # noqa: E501
TRANSFER_TOPIC = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
CVX_LOCKER_REWARD_PAID_TOPIC = b'T\x07\x98\xdfF\x8d{#\xd1\x1f\x15o\xdb\x95L\xb1\x9a\xd4\x14\xd1Pr*{mU\xba6\x9d\xeay.'  # noqa: E501
BOOSTER_WITHDRAW_TOPIC = b'\x92\xcc\xf4P\xa2\x86\xa9W\xafRP\x9b\xc1\xc9\x93\x9d\x1ajH\x17\x83\xe1B\xe4\x1e$\x99\xf0\xbbf\xeb\xc6'  # noqa: E501

WITHDRAWAL_TOPICS = {
    CVXCRV_WITHDRAWAL_TOPIC,
    CVX_WITHDRAW_TOPIC,
    BOOSTER_WITHDRAW_TOPIC,
}

REWARD_TOPICS = {
    CVXCRV_REWARD_PAID_TOPIC,
    CVX_LOCKER_REWARD_PAID_TOPIC,
}

# example transaction: https://etherscan.io/tx/0xe03d27127fda879144ea4cc587470bd37040be9921ff6a90f48d4efd0cb4fe13#eventlog  # noqa: E501
# data about abras is taken from: https://github.com/convex-eth/platform/blob/eb87f1fddcf5efcc4294f564b58cca7ac4ccbc90/contracts/contracts.json  # noqa: E501
CONVEX_ABRAS_HEX = {  # using set since we only need to check if an address is "in" these pools
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xd9$\x94\xcb\x92\x1e\\\r:9\xea\x88\xd0\x14{\xbd\x82\xe5\x10\x08',  # noqa: E501
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00YX\xa8\xdb}\xfe\x0c\xc4\x93\x82 \x90i\xb0\x0fT\xe1y)\xc2',  # noqa: E501
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb6^\xde\x13E!\xf0\xef\xd4\xe9C\xc85\xf4P\x13}\xc6\xe8>',  # noqa: E501
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00;\xa2\x07\xc2Z'\x85$\xe1\xcc\x7f\xaa\xea\x95\x07S\x04\x90r\xa4",  # noqa: E501
}

# ABI that is used for all convex reward pools to get balances
CONVEX_BALANCE_ABI = [{"inputs": [{"internalType": "address", "name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}]  # noqa: E501


CONVEX_POOLS = {  # mapping of pool rewards address: pool name
    string_to_evm_address('0xf34DFF761145FF0B05e917811d488B441F33a968'): 'cDAI+cUSDC',
    string_to_evm_address('0x8B55351ea358e5Eda371575B031ee24F462d503e'): 'cDAI+cUSDC+USDT',
    string_to_evm_address('0xd802a8351A76ED5eCd89A7502Ca615F2225A585d'): 'yDAI+yUSDC+yUSDT+yTUSD',  # noqa: E501
    string_to_evm_address('0x602c4cD53a715D8a7cf648540FAb0d3a2d546560'): 'yDAI+yUSDC+yUSDT+yBUSD',  # noqa: E501
    string_to_evm_address('0x22eE18aca7F3Ee920D01F25dA85840D12d98E8Ca'): 'crvPlain3andSUSD',
    string_to_evm_address('0xe3DaafC8C14147d5B4A7a56F0BfdED240158e51e'): 'ypaxCrv',
    string_to_evm_address('0x8E299C62EeD737a5d5a53539dF37b5356a27b07D'): 'crvRenWBTC',
    string_to_evm_address('0xd727A5A6D1C7b31Ff9Db4Db4d24045B7dF0CFF93'): 'crvRenWSBTC',
    string_to_evm_address('0x618BD6cBA676a46958c63700C04318c84a7b7c0A'): 'hCRV',
    string_to_evm_address('0x689440f2Ff927E1f24c72F1087E1FAF471eCe1c8'): '3Crv',
    string_to_evm_address('0x7A7bBf95C44b144979360C3300B54A7D34b44985'): 'gusd3CRV',
    string_to_evm_address('0x353e489311b21355461353fEC2d02B73EF0eDe7f'): 'husd3CRV',
    string_to_evm_address('0xa50e9071aCaD20b31cd2bbe4dAa816882De82BBe'): 'usdk3CRV',
    string_to_evm_address('0x4a2631d090e8b40bBDe245e687BF09e5e534A239'): 'usdn3CRV',
    string_to_evm_address('0xDBFa6187C79f4fE4Cda20609E75760C5AaE88e52'): 'musd3CRV',
    string_to_evm_address('0xedfCCF611D7c40F43e77a1340cE2C29EEEC27205'): 'rsv3CRV',
    string_to_evm_address('0x081A6672f07B615B402e7558a867C97FA080Ce35'): 'tbtc/sbtcCrv',
    string_to_evm_address('0x1992b82A8cCFC8f89785129D6403b13925d6226E'): 'dusd3CRV',
    string_to_evm_address('0x2d3C90AEB11D1393CA839Afc9587515B1325D77A'): 'pBTC/sbtcCRV',
    string_to_evm_address('0x61D741045cCAA5a215cF4E5e55f20E1199B4B843'): 'bBTC/sbtcCRV',
    string_to_evm_address('0xeeeCE77e0bc5e59c77fc408789A9A172A504bD2f'): 'oBTC/sbtcCRV',
    string_to_evm_address('0xd4Be1911F8a0df178d6e7fF5cE39919c273E2B7B'): 'ust3CRV',
    string_to_evm_address('0xcB8F69E0064d8cdD29cbEb45A14cf771D904BcD3'): 'eursCRV',
    string_to_evm_address('0x192469CadE297D6B21F418cFA8c366b63FFC9f9b'): 'eCRV',
    string_to_evm_address('0xE82c1eB4BC6F92f85BF7EB6421ab3b882C3F5a7B'): 'a3CRV',
    string_to_evm_address('0x0A760466E1B4621579a82a39CB56Dda2F4E70f03'): 'steCRV',
    string_to_evm_address('0xF86AE6790654b70727dbE58BF1a863B270317fD0'): 'saCRV',
    string_to_evm_address('0x8798b81b0261934aa850C8de8622472bfdc143F4'): 'ankrCRV',
    string_to_evm_address('0x24DfFd1949F888F91A0c8341Fc98a3F280a782a8'): 'usdp3CRV',
    string_to_evm_address('0x3E03fFF82F77073cc590b656D42FceB12E4910A8'): 'ib3CRV',
    string_to_evm_address('0x9700152175dc22E7d1f3245fE3c1D2cfa3602548'): 'linkCRV',
    string_to_evm_address('0x308b48F037AAa75406426dACFACA864ebd88eDbA'): 'TUSD3CRV-f',
    string_to_evm_address('0xB900EF131301B307dB5eFcbed9DBb50A3e209B2e'): 'FRAX3CRV-f',
    string_to_evm_address('0x2ad92A7aE036a038ff02B96c88de868ddf3f8190'): 'LUSD3CRV-f',
    string_to_evm_address('0xbD223812d360C9587921292D0644D18aDb6a2ad0'): 'BUSD3CRV-f',
    string_to_evm_address('0x61dB6c2321f784c8fAb8d5eF80f58F27C831dCc8'): 'rCRV',
    string_to_evm_address('0x02E2151D4F351881017ABdF2DD2b51150841d5B3'): 'alUSD3CRV-f',
    string_to_evm_address('0x5Edced358e6C0B435D53CC30fbE6f5f0833F404F'): 'crvTricrypto',
    string_to_evm_address('0x9D5C5E364D81DaB193b72db9E9BE9D8ee669B652'): 'crv3crypto',
    string_to_evm_address('0xD814BFC091111E1417a669672144aFFAA081c3CE'): 'EURT-f',
    string_to_evm_address('0xFd5AbF66b003881b88567EB9Ed9c651F14Dc4771'): 'MIM-3LP3CRV-f',
    string_to_evm_address('0x0392321e86F42C2F94FBb0c6853052487db521F0'): 'cvxcrv-f',
    string_to_evm_address('0xbA8fE590498ed24D330Bb925E69913b1Ac35a81E'): 'ibJPY+sJPY-f',
    string_to_evm_address('0x51a16DA36c79E28dD3C8c0c19214D8aF413984Aa'): 'ibGBP+sGBP-f',
    string_to_evm_address('0xb1Fae59F23CaCe4949Ae734E63E42168aDb0CcB3'): 'ibAUD+sAUD-f',
    string_to_evm_address('0xCd0559ADb6fAa2fc83aB21Cf4497c3b9b45bB29f'): 'ibEUR+sEUR-f',
    string_to_evm_address('0xa5A5905efc55B05059eE247d5CaC6DD6791Cfc33'): 'ibCHF+sCHF-f',
    string_to_evm_address('0x8F18C0AF0d7d511E8Bdc6B3c64926B04EDfE4892'): 'ibKRW+sKRW-f',
    string_to_evm_address('0xc3628b8FAaDe10aCeAe88c9b982cE0AAc9bBaaD3'): 'cvxRT',
    string_to_evm_address('0x48Bc302d8295FeA1f8c3e7F57D4dDC9981FEE410'): 'alETH+ETH-f',
    string_to_evm_address('0x7CDA2a83D29d7Fc2ccb8F7716b5c1c34781aeb12'): 'EURN/EURT-f',
    string_to_evm_address('0xA689C00F3fd87dD3871C79C73343cd9F7957377E'): 'USDM3CRV-f',
    string_to_evm_address('0xC62DE533ea77D46f3172516aB6b1000dAf577E89'): 'MIM-UST-f',
    string_to_evm_address('0x4F2b8a15d0Dd58c1eB60bd53e966872828519Cee'): 'ibbtc/sbtcCRV-f',
    string_to_evm_address('0xb0c1B7b83Baae51284B8BbBa02Ec37742440199d'): 'crvEURSUSDC',
    string_to_evm_address('0xD2B756Af4E345A8657C0656C148aDCD3000C97A4'): 'crvEURTUSD',
    string_to_evm_address('0x7D536a737C13561e0D2Decf1152a653B4e615158'): 'OUSD3CRV-f',
    string_to_evm_address('0x500E169c15961DE8798Edb52e0f88a8662d30EC5'): 'pax-usdp3CRV-f',
    string_to_evm_address('0x329cb014b562d5d42927cfF0dEdF4c13ab0442EF'): 'D3-f',
    string_to_evm_address('0x7e2b9B5244bcFa5108A76D5E7b507CFD5581AD4A'): 'UST_whv23CRV-f',
    string_to_evm_address('0x4a9b7eDD67f58654a2c33B587f98c5709AC7d482'): '3EURpool-f',
    string_to_evm_address('0x085A2054c51eA5c91dbF7f90d65e728c0f2A270f'): 'crvCRVETH',
    string_to_evm_address('0x835f69e58087E5B6bffEf182fe2bf959Fe253c3c'): 'DOLA3POOL3CRV-f',
    string_to_evm_address('0x29B91c6CEC4F43aFdb6f6d71FAf1C03d6b712f55'): 'RAI3CRV',
    string_to_evm_address('0xb1Fb0BA0676A1fFA83882c7F4805408bA232C1fA'): 'crvCVXETH',
    string_to_evm_address('0x6cb1933E49C48AE8ec12d39aD7D85695b247deDB'): 'crvXAUTUSD',
    string_to_evm_address('0xb2f0bB6352417c1Bf017862aC165E67623611aF3'): 'crvSPELLETH',
    string_to_evm_address('0x3E91E7c822AC8b4b7905d108c3faCF22A3ee5d2c'): 'crvTETH',
    string_to_evm_address('0x3207bDc327aB67f182B82948fd3DF757F8771324'): 'YFIETH-f',
    string_to_evm_address('0xAA0e8Ef60BaBda02Ef11c89a061D82b1D61a462C'): 'FXSETH-f',
    string_to_evm_address('0x769499A7B4093b2AA35E3F3C00B1ab5dc8EF7146'): 'ag+ib-EUR-f',
    string_to_evm_address('0x3133A4428AAC0b4ad96a09845363386ECd289A9c'): 'FEI3CRV3CRV-f',
    string_to_evm_address('0xf27AFAD0142393e4b3E5510aBc5fe3743Ad669Cb'): 'cvxFXSFXS-f',
    string_to_evm_address('0x5c463069b99AfC9333F4dC2203a9f0c6C7658cCc'): 'rETHwstETH-f',
    string_to_evm_address('0x36c7E7F9031647A74687ce46A8e16BcEA84f3865'): 'BADGERWBTC-f',
    string_to_evm_address('0x41565A76DC949E57486Ca4550C2e086D95AEfb19'): 'BTRFLYETH-f',
    string_to_evm_address('0xC4d009E61a904BfDf39144295F12870E8305D4d9'): 'PWRD3CRV-f',
    string_to_evm_address('0x589761B61D8d1C8ecc36F3cFE35932670749015a'): 'pbtc/sbtcCRV-f',
    string_to_evm_address('0xE259d085f55825624bBA8571eD20984c125Ba720'): 'silofrax-f',
    string_to_evm_address('0x8731A63dD6aF83c044F623A89ABD50A8bb5a5022'): 'CADCUSDC-f',
    string_to_evm_address('0x414d43EfDf60010428B55CEEE5fec187E2ebB284'): 'BEAN3CRV-f',
    string_to_evm_address('0x87d258F95Cf6D6d13E3c9D5365dD7B46EF050FbF'): 'LFTETH-f',
    string_to_evm_address('0x1A8D59cCbbC81ecD556B86969680faD2F238F18f'): 'FPIFRAX-f',
    string_to_evm_address('0xeBd7E324b6b086986efb97804929538Bf4bF2047'): 'SDTETH-f',
    string_to_evm_address('0xbAFC4FAeB733C18411886A04679F11877D8629b1'): 'ibAUDUSDC-f',
    string_to_evm_address('0x9BEc26bDd9702F4e0e4de853dd65Ec75F90b1F2e'): 'ibCHFUSDC-f',
    string_to_evm_address('0xAab7202D93B5633eB7FB3b80873C817B240F6F44'): 'ibEURUSDC-f',
    string_to_evm_address('0x8C87E32000ADD1a7D7D69a1AE180C415AF769361'): 'ibGBPUSDC-f',
    string_to_evm_address('0x58563C872c791196d0eA17c4E53e77fa1d381D4c'): 'ibJPYUSDC-f',
    string_to_evm_address('0x1900249c7a90D27b246032792004FF0E092Ac2cE'): 'ibKRWUSDC-f',
    string_to_evm_address('0x0c2da920E577960f39991030CfBdd4cF0a0CfEBD'): 'KP3RETH-f',
    string_to_evm_address('0x83a3CE160915675F5bC7cC3CfDA5f4CeBC7B7a5a'): 'PUSd-3CRV-f',
    string_to_evm_address('0xd683C7051a28fA150EB3F4BD92263865D4a67778'): 'OHMETH-f',
    string_to_evm_address('0xA7FC7e90c45C2657A9069CA99011894a76eaB82D'): 'sdCRVCRV-f',
    string_to_evm_address('0xC5B3B2537499e3943C9A359886193F3F89EdDc6a'): 'sdAGAG-f',
    string_to_evm_address('0x17E3Bc273cFcB972167059E55104DBCC8f8431bE'): 'STGUSDC-f',
    string_to_evm_address('0x7D475cc8A5E0416f0e63042547aDB94ca7045A5b'): 'USDD3CRV3CRV-f',
    string_to_evm_address('0xcc4687A893C1Fa137e0CAcd96591422dEb7B717c'): 'PALETH-f',
    string_to_evm_address('0xA84f2187371e8A61fa6634eCB3Ff6D89dF299e0e'): 'sdFXSFXS-f',
    string_to_evm_address('0x3382607d00cfb668AbaB80D8EE781a2720CbC9ea'): 'TOKEETH-f',
    string_to_evm_address('0x7e880867363A7e321f5d260Cade2B0Bb2F717B02'): 'crvFRAX',
    string_to_evm_address('0x3fABBDfe05487De1720a9420fE2e16d2c3e79A9D'): 'SUSDFRAXBP3CRV-f',
    string_to_evm_address('0x053e1dad223A206e6BCa24C77786bb69a10e427d'): 'LUSDFRAXBP3CRV-f',
    string_to_evm_address('0x51e6B84968D56a1E5BC93Ee264e95b1Ea577339c'): 'APEUSDBP3CRV-f',
    string_to_evm_address('0x47809eE386D1dEC29c0b13f21ba30F564517538B'): 'GUSDFRAXBP3CRV-f',
    string_to_evm_address('0x9e6Daf019767D5cEAdE416ce77E8d187b5B254F3'): 'BUSDFRAXBP3CRV-f',
    string_to_evm_address('0x26598e3E511ADFadefD70ab2C3475Ff741741104'): 'alUSDFRAXB3CRV-f',
    string_to_evm_address('0x546cd3B917c1d8A6525b4A312bB0014BE031Eb28'): 'USDDFRAXBP3CRV-f',
    string_to_evm_address('0x4a744870fD705971c8c00aC510eAc2206C93d5bb'): 'TUSDFRAXBP3CRV-f',
    string_to_evm_address('0x43217822E188b39E90AFA54A5fcf1c76AB0F323a'): 'xFraxTplLP-f',
}


# Example transaction: https://etherscan.io/tx/0x5e62ce39159fcdf528905d044e5387c8f21a1eca015d08cebc652bfb9c183611  # noqa: E501
# Data taken from: https://etherscan.io/find-similar-contracts?a=0x7091dbb7fcba54569ef1387ac89eb2a5c9f6d2ea  # noqa: E501
# Convex might use virtual rewards pool as well as regular rewards, so we need to handle it.
CONVEX_VIRTUAL_REWARDS = [
    string_to_evm_address('0x7091dbb7fcbA54569eF1387Ac89Eb2a5C9F6d2EA'),
    string_to_evm_address('0x81fCe3E10D12Da6c7266a1A169c4C96813435263'),
    string_to_evm_address('0x7c41906Df8395AF4387fA79B85c845069f88eeC3'),
    string_to_evm_address('0x008aEa5036b819B4FEAEd10b2190FBb3954981E8'),
    string_to_evm_address('0x177252Ac74f1D77513971aA85AF7009C43EcdEe2'),
    string_to_evm_address('0xc095Cec98a9f8Ad6D2baA282A8e6bE246f98BD25'),
    string_to_evm_address('0x55d59b791f06dc519B176791c4E037E8Cf2f6361'),
    string_to_evm_address('0x93A5C724c4992FCBDA6b96F06fa15EB8B5c485b7'),
    string_to_evm_address('0x00469d388b06127221D6310843A43D079eb2bB18'),
    string_to_evm_address('0x20165075174b51a2f9Efbf7d6D8F3c72BBc63064'),
    string_to_evm_address('0x2Aa030dCB729CF94bc096Bd00d377aA719A09371'),
    string_to_evm_address('0xAE97D3766924526084dA88ba9B2bd7aF989Bf6fC'),
    string_to_evm_address('0x94C259DC4C6dF248B0b5D23C055CB7574A587d67'),
    string_to_evm_address('0xAF138B29205c2246B069Ed8f0b213b205FBc14E0'),
    string_to_evm_address('0xcDEC6714eB482f28f4889A0c122868450CDBF0b0'),
    string_to_evm_address('0x666F8eEE6FD6839853993977CC86a7A51425673C'),
    string_to_evm_address('0x681A790debE586A64eea055BF0983CD6629d8359'),
    string_to_evm_address('0xd731495bb78a4250bC094686788F3fF890dEe0f4'),
    string_to_evm_address('0x22a07a6bdA1CECbe2a671203e2114d8A170E5529'),
    string_to_evm_address('0x69a92f1656cd2e193797546cFe2EaF32EACcf6f7'),
    string_to_evm_address('0xbE4DEa8E5d1E53FAd661610E47501f858F25852D'),
    string_to_evm_address('0x771bc5c888d1B318D0c5b177e4F996d3D5fd3d18'),
    string_to_evm_address('0xE689DB5D753abc411ACB8a3fEf226C08ACDAE13f'),
    string_to_evm_address('0x91ad51F0897552ce77f76B44e9a86B4Ad2B28c25'),
    string_to_evm_address('0x21034ccc4f8D07d0cF8998Fdd4c45e426540dEc1'),
    string_to_evm_address('0x9D9EBCc8E7B4eF061C0F7Bab532d1710b874f789'),
    string_to_evm_address('0xE3A64E08EEbf38b19a3d9fec51d8cD5A8898Dd5e'),
    string_to_evm_address('0x8a3F52c2Eb02De2d8356a8286c96909352c62B10'),
    string_to_evm_address('0x00A4f5d12E3FAA909c53CDcC90968F735633e988'),
    string_to_evm_address('0x040A6Ae6314e190974ee4839f3c2FBf849EF54Eb'),
    string_to_evm_address('0xbA5eF047ce02cc0096DB3Bc8ED84aAD14291f8a0'),
    string_to_evm_address('0x1c86460640457466E2eC86916B4a91ED86CE0D1E'),
    string_to_evm_address('0x93649cd43635bC5F7Ad8fA2fa27CB9aE765Ec58A'),
    string_to_evm_address('0x5F91615268bE6b4aDD646b2560785B8F17dccBb4'),
    string_to_evm_address('0xCEc9a6efFf1daF52aF12beeBf87F81bda7b95c0b'),
    string_to_evm_address('0x27801399D60594BFeDe955D54c3e85B2f00179c5'),
    string_to_evm_address('0xb9E2e39c9C804a01f1FCB4e86F765774D511D535'),
    string_to_evm_address('0xAAf75a94394F6D06E01CcE62e2545CeFFBFA1E2D'),
    string_to_evm_address('0x880c2c5c4eA8cef892a90E3f714eB60144C08c30'),
    string_to_evm_address('0x08EDE581D9B9ae55FA7deCc4E4331D191BbBF9dB'),
    string_to_evm_address('0x8A05801c1512F6018e450b0F69e9Ca7b985fCea3'),
    string_to_evm_address('0x28a68d9c58086dAeB32d5c9297366cc91e50215D'),
    string_to_evm_address('0x74835A39Fd0e72E142d5E83D514e3eF6E7642220'),
    string_to_evm_address('0xE1eCBB4181378E2346EAC90Eb5606c01Aa08f052'),
    string_to_evm_address('0xb83EaADa3757432f7a894944C3ac154FbdBD8B46'),
    string_to_evm_address('0x834B9147Fd23bF131644aBC6e557Daf99C5cDa15'),
    string_to_evm_address('0xE2585F27bf5aaB7756f626D6444eD5Fc9154e606'),
    string_to_evm_address('0x28120D9D49dBAeb5E34D6B809b842684C482EF27'),
    string_to_evm_address('0x92dFd397b6d0B878126F5a5f6F446ae9Fc8A8356'),
    string_to_evm_address('0x19Ba12D57aD7B126dE898706AA6dBF7d6DC85FF8'),
    string_to_evm_address('0x640eBdA6C4f8D70A484C170106478ffb289a47DA'),
    string_to_evm_address('0xd48ad508E4e6d18bBBcA5042199e6b627dfCb331'),
    string_to_evm_address('0x498Dd51c2059D7e3008067841d1efE12D6c7F99c'),
    string_to_evm_address('0xe826994Cd8d4271A4b410B1b47e7DE5774Ba6E7A'),
    string_to_evm_address('0x3Ac6Ef1e811bACfa283ECC25ACAD1Cb858957bAb'),
    string_to_evm_address('0x5ab9Ea799904185939209c30Aa180f84AC58A63b'),
    string_to_evm_address('0x8E8E06F0555CA7A33C2c1a4e01875CEbF05Bda00'),
    string_to_evm_address('0x1BeCd991e1c5D0162718A215016d83E077a04cE9'),
    string_to_evm_address('0xCB200C57A6ef34a2e6bBfb5E02c3e44097F259Ee'),
]
