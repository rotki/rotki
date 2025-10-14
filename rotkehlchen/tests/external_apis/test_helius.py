from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import call, patch

import pytest

from rotkehlchen.db.filtering import SolanaTransactionsFilterQuery
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.externalapis.helius import HELIUS_API_URL, Helius
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.factories import make_solana_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ApiKey, ExternalService, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

JUPITER_SWAP_TX_RESPONSE: Final = '[{"description":"","type":"UNKNOWN","source":"UNKNOWN","fee":10195,"feePayer":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","signature":"5vBFfTGrcdkE7ZdsUDSU2kRkhoFp4EgKtLLB6h2m1uQoG5wCddCkFGnNjXaHrV2r1kZ8CpJfh7UcWJ9tFXAyKc8Q","slot":367689024,"timestamp":1758217531,"tokenTransfers":[{"fromTokenAccount":"DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","toTokenAccount":"HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","fromUserAccount":"7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","toUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","tokenAmount":0.00287442,"mint":"7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs","tokenStandard":"Fungible"},{"fromTokenAccount":"BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","toTokenAccount":"ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","fromUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","toUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","tokenAmount":0.052708178,"mint":"So11111111111111111111111111111111111111112","tokenStandard":"Fungible"}],"nativeTransfers":[{"fromUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","toUserAccount":"ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","amount":2039280},{"fromUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","toUserAccount":"7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","amount":52708178},{"fromUserAccount":"ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","toUserAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","amount":54747458}],"accountData":[{"account":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","nativeBalanceChange":-10195,"tokenBalanceChanges":[]},{"account":"7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","nativeBalanceChange":52708178,"tokenBalanceChanges":[]},{"account":"DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","nativeBalanceChange":0,"tokenBalanceChanges":[{"userAccount":"7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","tokenAccount":"DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","rawTokenAmount":{"tokenAmount":"-287442","decimals":8},"mint":"7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"}]},{"account":"ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","nativeBalanceChange":-52708178,"tokenBalanceChanges":[{"userAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","tokenAccount":"BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","rawTokenAmount":{"tokenAmount":"-52708178","decimals":9},"mint":"So11111111111111111111111111111111111111112"}]},{"account":"HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","nativeBalanceChange":0,"tokenBalanceChanges":[{"userAccount":"7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","tokenAccount":"HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","rawTokenAmount":{"tokenAmount":"287442","decimals":8},"mint":"7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"}]},{"account":"11111111111111111111111111111111","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"ComputeBudget111111111111111111111111111111","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"So11111111111111111111111111111111111111112","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"61DFfeTKM7trxYcPQCM78bJ794ddZprZpAwAnLiwTpYH","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs","nativeBalanceChange":0,"tokenBalanceChanges":[]}],"transactionError":null,"instructions":[{"accounts":[],"data":"3Ddz2qHp11eo","programId":"ComputeBudget111111111111111111111111111111","innerInstructions":[]},{"accounts":[],"data":"FV2PdR","programId":"ComputeBudget111111111111111111111111111111","innerInstructions":[]},{"accounts":["7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY","7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","61DFfeTKM7trxYcPQCM78bJ794ddZprZpAwAnLiwTpYH","BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs","TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","So11111111111111111111111111111111111111112","TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","11111111111111111111111111111111","ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj"],"data":"HoSdaJgwWtUbjM99F3S6JbDjpMBo54SfrpbRD2guKECL96pP","programId":"61DFfeTKM7trxYcPQCM78bJ794ddZprZpAwAnLiwTpYH","innerInstructions":[{"accounts":["DEN9VJCeUhyvHR4y5VruahjkqcZHZopyXjdCi9tY8iY","HgLC8cAuUgrt9d2MVmGUiUWgwo2bs7wcaTvWSP2znmcQ","7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY"],"data":"3peYHhHYfToD","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj"],"data":"11119os1e9qSs2u7TsThXqkBSRVFxhmYaFKFZ1waB2X7armDmvK3p5GmLdUxYdg3h7QSrL","programId":"11111111111111111111111111111111"},{"accounts":["ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","So11111111111111111111111111111111111111112"],"data":"6TzQdiY1vUxPdN7EL5BHWAHaLdefTocuM8W7bLWVYttDN","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["BJqrMMVFrMTM9V93w2JN2uv73WX9JxZgEbbFdevWEt6x","ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ"],"data":"3TDcKxZ3zT7u","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["ebh8CfuhRd1VhSNuFqTY3srFkGfBn6giJTgAQN81VUj","7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ"],"data":"A","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ","7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY"],"data":"3Bxs4EchykAmQrVD","programId":"11111111111111111111111111111111"}]}],"events":{}}]'  # noqa: E501
TX_MISSING_TOKEN_ACCOUNT_INFO: Final = '[{"description":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh swapped 24.780010555 AURY for 52.293757 USDC","type":"SWAP","source":"JUPITER","fee":5000,"feePayer":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","signature":"2h1iMn8Dd6i2n8MmdVXyxXzru8uYzFqukSYvo4Kmb4cr7xGZamghA6B7Bj7TjANc4B7Fs8j5UyB3RfxdxuFHJkzk","slot":145500148,"timestamp":1660207391,"tokenTransfers":[{"fromTokenAccount":"7SJn9dpze9RSDfczXyA6r7BqNeSPvaBwZLdMZr7o12QM","toTokenAccount":"413s6jiRbayD9didA4VnY8kQVgVBgkYNpYB2tyNf8sbh","fromUserAccount":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","toUserAccount":"9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ","tokenAmount":24.780010555,"mint":"AURYydfxJib1ZkTir1Jn1J9ECYUtjb6rKQVmtYaixWPP","tokenStandard":"Fungible"},{"fromTokenAccount":"GdPeogNxRWAZtUj7ZHc7fUpBuGHJosdbukiT2krFtXm8","toTokenAccount":"UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB","fromUserAccount":"9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ","toUserAccount":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","tokenAmount":52.293757,"mint":"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v","tokenStandard":"Fungible"},{"fromTokenAccount":"","toTokenAccount":"JCqbv7r3mtYhzruNFjc21X14fndDVBLMiaNQrsHVpWui","fromUserAccount":"","toUserAccount":"2YM8LrJGRtsDcWeqsjX2EQwJfhArxyDdtDzgt7vrwwbV","tokenAmount":0.063025,"mint":"6mJqqT5TMgveDvxzBt3hrjGkPV5VAj7tacxFCT3GebXh","tokenStandard":"Fungible"}],"nativeTransfers":[],"accountData":[{"account":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","nativeBalanceChange":-5000,"tokenBalanceChanges":[]},{"account":"413s6jiRbayD9didA4VnY8kQVgVBgkYNpYB2tyNf8sbh","nativeBalanceChange":0,"tokenBalanceChanges":[{"userAccount":"9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ","tokenAccount":"413s6jiRbayD9didA4VnY8kQVgVBgkYNpYB2tyNf8sbh","rawTokenAmount":{"tokenAmount":"24780010555","decimals":9},"mint":"AURYydfxJib1ZkTir1Jn1J9ECYUtjb6rKQVmtYaixWPP"}]},{"account":"6mJqqT5TMgveDvxzBt3hrjGkPV5VAj7tacxFCT3GebXh","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"7SJn9dpze9RSDfczXyA6r7BqNeSPvaBwZLdMZr7o12QM","nativeBalanceChange":0,"tokenBalanceChanges":[{"userAccount":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","tokenAccount":"7SJn9dpze9RSDfczXyA6r7BqNeSPvaBwZLdMZr7o12QM","rawTokenAmount":{"tokenAmount":"-24780010555","decimals":9},"mint":"AURYydfxJib1ZkTir1Jn1J9ECYUtjb6rKQVmtYaixWPP"}]},{"account":"Edg9J3CMky9AVJq2WrSar2JR38jFkg4S7vAW7Xsix8oV","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"GdPeogNxRWAZtUj7ZHc7fUpBuGHJosdbukiT2krFtXm8","nativeBalanceChange":0,"tokenBalanceChanges":[{"userAccount":"9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ","tokenAccount":"GdPeogNxRWAZtUj7ZHc7fUpBuGHJosdbukiT2krFtXm8","rawTokenAmount":{"tokenAmount":"-52293757","decimals":6},"mint":"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"}]},{"account":"JCqbv7r3mtYhzruNFjc21X14fndDVBLMiaNQrsHVpWui","nativeBalanceChange":0,"tokenBalanceChanges":[{"userAccount":"2YM8LrJGRtsDcWeqsjX2EQwJfhArxyDdtDzgt7vrwwbV","tokenAccount":"JCqbv7r3mtYhzruNFjc21X14fndDVBLMiaNQrsHVpWui","rawTokenAmount":{"tokenAmount":"63025","decimals":6},"mint":"6mJqqT5TMgveDvxzBt3hrjGkPV5VAj7tacxFCT3GebXh"}]},{"account":"UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB","nativeBalanceChange":0,"tokenBalanceChanges":[{"userAccount":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","tokenAccount":"UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB","rawTokenAmount":{"tokenAmount":"52293757","decimals":6},"mint":"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"}]},{"account":"6HSguUukDH9zqJBm6oAAmFkg1WK9dJ5iLgnppTCM6jHm","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"JUP2jxvXaqu7NQY1GmNF4m1vodw12LVXYxbFL2uJvfo","nativeBalanceChange":0,"tokenBalanceChanges":[]},{"account":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","nativeBalanceChange":0,"tokenBalanceChanges":[]}],"transactionError":null,"instructions":[{"accounts":["Edg9J3CMky9AVJq2WrSar2JR38jFkg4S7vAW7Xsix8oV","UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB"],"data":"fC8nMvWeAaD","programId":"JUP2jxvXaqu7NQY1GmNF4m1vodw12LVXYxbFL2uJvfo","innerInstructions":[]},{"accounts":["9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP","TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","6HSguUukDH9zqJBm6oAAmFkg1WK9dJ5iLgnppTCM6jHm","9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ","AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","7SJn9dpze9RSDfczXyA6r7BqNeSPvaBwZLdMZr7o12QM","413s6jiRbayD9didA4VnY8kQVgVBgkYNpYB2tyNf8sbh","GdPeogNxRWAZtUj7ZHc7fUpBuGHJosdbukiT2krFtXm8","UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB","6mJqqT5TMgveDvxzBt3hrjGkPV5VAj7tacxFCT3GebXh","JCqbv7r3mtYhzruNFjc21X14fndDVBLMiaNQrsHVpWui"],"data":"6kT8niHk82HZ83J7fAbsb3ciH8fKG6UeAVD1","programId":"JUP2jxvXaqu7NQY1GmNF4m1vodw12LVXYxbFL2uJvfo","innerInstructions":[{"accounts":["6HSguUukDH9zqJBm6oAAmFkg1WK9dJ5iLgnppTCM6jHm","9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ","AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","7SJn9dpze9RSDfczXyA6r7BqNeSPvaBwZLdMZr7o12QM","413s6jiRbayD9didA4VnY8kQVgVBgkYNpYB2tyNf8sbh","GdPeogNxRWAZtUj7ZHc7fUpBuGHJosdbukiT2krFtXm8","UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB","6mJqqT5TMgveDvxzBt3hrjGkPV5VAj7tacxFCT3GebXh","JCqbv7r3mtYhzruNFjc21X14fndDVBLMiaNQrsHVpWui","TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"],"data":"rPXaeqpXmsVv36a3sSf4DV","programId":"9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP"},{"accounts":["7SJn9dpze9RSDfczXyA6r7BqNeSPvaBwZLdMZr7o12QM","413s6jiRbayD9didA4VnY8kQVgVBgkYNpYB2tyNf8sbh","AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh"],"data":"3PVBb9AUcwCb","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["6mJqqT5TMgveDvxzBt3hrjGkPV5VAj7tacxFCT3GebXh","JCqbv7r3mtYhzruNFjc21X14fndDVBLMiaNQrsHVpWui","9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ"],"data":"6K6L3qCXHtGo","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"accounts":["GdPeogNxRWAZtUj7ZHc7fUpBuGHJosdbukiT2krFtXm8","UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB","9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ"],"data":"3aXKSCf3ahTu","programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}]}],"events":{"swap":{"nativeInput":null,"nativeOutput":null,"tokenInputs":[{"userAccount":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","tokenAccount":"7SJn9dpze9RSDfczXyA6r7BqNeSPvaBwZLdMZr7o12QM","rawTokenAmount":{"tokenAmount":"24780010555","decimals":9},"mint":"AURYydfxJib1ZkTir1Jn1J9ECYUtjb6rKQVmtYaixWPP"}],"tokenOutputs":[{"userAccount":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","tokenAccount":"UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB","rawTokenAmount":{"tokenAmount":"52293757","decimals":6},"mint":"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"}],"nativeFees":[],"tokenFees":[{"userAccount":"","tokenAccount":"","rawTokenAmount":{"tokenAmount":"63025","decimals":6},"mint":"6mJqqT5TMgveDvxzBt3hrjGkPV5VAj7tacxFCT3GebXh"}],"innerSwaps":[{"tokenInputs":[{"fromTokenAccount":"7SJn9dpze9RSDfczXyA6r7BqNeSPvaBwZLdMZr7o12QM","toTokenAccount":"413s6jiRbayD9didA4VnY8kQVgVBgkYNpYB2tyNf8sbh","fromUserAccount":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","toUserAccount":"9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ","tokenAmount":24.780010555,"mint":"AURYydfxJib1ZkTir1Jn1J9ECYUtjb6rKQVmtYaixWPP","tokenStandard":"Fungible"}],"tokenOutputs":[{"fromTokenAccount":"GdPeogNxRWAZtUj7ZHc7fUpBuGHJosdbukiT2krFtXm8","toTokenAccount":"UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB","fromUserAccount":"9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ","toUserAccount":"AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh","tokenAmount":52.293757,"mint":"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v","tokenStandard":"Fungible"}],"tokenFees":[{"fromTokenAccount":"","toTokenAccount":"JCqbv7r3mtYhzruNFjc21X14fndDVBLMiaNQrsHVpWui","fromUserAccount":"","toUserAccount":"2YM8LrJGRtsDcWeqsjX2EQwJfhArxyDdtDzgt7vrwwbV","tokenAmount":0.063025,"mint":"6mJqqT5TMgveDvxzBt3hrjGkPV5VAj7tacxFCT3GebXh","tokenStandard":"Fungible"}],"nativeFees":[],"programInfo":{"source":"ORCA","account":"9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP","programName":"ORCA_TOKEN_SWAP_V2","instructionName":"tokenSwap"}}]}}}]'  # noqa: E501


@pytest.fixture(name='mock_helius')
def fixture_mock_helius(database: 'DBHandler') -> Helius:
    """Create helius with a fake api key so it doesn't do a missing api key error.
    Any Helius api requests must be mocked.
    """
    with database.user_write() as write_cursor:
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.HELIUS,
                api_key=ApiKey('xyz'),
            )])

    return Helius(database=database)


def test_get_transactions(mock_helius: Helius) -> None:
    """Test that querying transactions from the Helius API works correctly.
    Simulates batched requests and checks that a tx is deserialized properly
    from the mocked api response.
    """
    swap_tx_signature = '5vBFfTGrcdkE7ZdsUDSU2kRkhoFp4EgKtLLB6h2m1uQoG5wCddCkFGnNjXaHrV2r1kZ8CpJfh7UcWJ9tFXAyKc8Q'  # noqa: E501

    def mock_post(url: str, json: dict[str, Any], **kwargs: Any) -> MockResponse:
        """Mock the Helius API post request."""
        if 'transactions' in json and swap_tx_signature in json['transactions']:
            response_text = JUPITER_SWAP_TX_RESPONSE
        else:
            response_text = '[]'

        return MockResponse(status_code=HTTPStatus.OK, text=response_text)

    with (
        patch('rotkehlchen.externalapis.helius.requests.post', side_effect=mock_post) as post_mock,
        patch('rotkehlchen.externalapis.helius.MAX_TX_BATCH_SIZE', new=2),  # Force pagination
    ):
        mock_helius.get_transactions(
            signatures=[
                swap_tx_signature,
                (other_tx_sig_1 := '4PXgKteR5ofZLbMGxNzstUc5f1GHLVoPh47FCaXLRETARUtym99DtW74EmxjazpQ94BJeMAPiYXEjiBGDeioj32y'),  # noqa: E501
                (other_tx_sig_2 := '5LB5yWMEqGZLTQxuSmU3un4dVZoCZbXBrQJnW2zXJhZu2WaYfdtUKpzwGPZk8AdRPQ9yqfFN5HetrgpDP6DWXx5a'),  # noqa: E501
            ],
            relevant_address=make_solana_address(),
        )

    # Check that requests are properly batched
    assert post_mock.call_args_list == [call(
        url=f'{HELIUS_API_URL}/transactions/?api-key=xyz',
        json={'transactions': [swap_tx_signature, other_tx_sig_1]},
        timeout=(timeout := CachedSettings().get_timeout_tuple()),
    ), call(
        url=f'{HELIUS_API_URL}/transactions/?api-key=xyz',
        json={'transactions': [other_tx_sig_2]},
        timeout=timeout,
    )]

    with mock_helius.db.conn.read_ctx() as cursor:
        txs = DBSolanaTx(mock_helius.db).get_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(),
        )

    assert len(txs) == 1  # the mocked response only includes tx data for the jupiter swap tx
    tx = txs[0]  # Check some properties of the deserialized transaction
    assert tx.signature == deserialize_tx_signature(swap_tx_signature)
    assert tx.fee == 10195
    assert tx.slot == 367689024
    assert tx.block_time == 1758217531
    assert tx.success is True
    assert len(tx.account_keys) == 12
    assert len(tx.instructions) == 9
    assert len([x for x in tx.instructions if x.parent_execution_index == 2]) == 6
    assert len([x for x in tx.instructions if x.parent_execution_index is None]) == 3


def test_tx_with_missing_token_account_info(mock_helius: Helius) -> None:
    """Regression test for a problem where a transaction with token transfer entries without
    complete token account info was causing the entire tx to fail to deserialize.
    """
    with patch(
        target='rotkehlchen.externalapis.helius.requests.post',
        return_value=MockResponse(
            status_code=HTTPStatus.OK,
            text=TX_MISSING_TOKEN_ACCOUNT_INFO,
        ),
    ):
        mock_helius.get_transactions(
            signatures=['2h1iMn8Dd6i2n8MmdVXyxXzru8uYzFqukSYvo4Kmb4cr7xGZamghA6B7Bj7TjANc4B7Fs8j5UyB3RfxdxuFHJkzk'],
            relevant_address=make_solana_address(),
        )

    with mock_helius.db.conn.read_ctx() as cursor:
        assert len(DBSolanaTx(mock_helius.db).get_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(),
        )) == 1
        assert cursor.execute('SELECT * FROM key_value_cache').fetchall() == [
            ('solana_token_account_7SJn9dpze9RSDfczXyA6r7BqNeSPvaBwZLdMZr7o12QM', 'AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh,AURYydfxJib1ZkTir1Jn1J9ECYUtjb6rKQVmtYaixWPP'),  # noqa: E501
            ('solana_token_account_413s6jiRbayD9didA4VnY8kQVgVBgkYNpYB2tyNf8sbh', '9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ,AURYydfxJib1ZkTir1Jn1J9ECYUtjb6rKQVmtYaixWPP'),  # noqa: E501
            ('solana_token_account_GdPeogNxRWAZtUj7ZHc7fUpBuGHJosdbukiT2krFtXm8', '9T1koZp2PNJgspcx3G22yLiChBUfYzAjs2dhj2kgw2LZ,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),  # noqa: E501
            ('solana_token_account_UdSeHSj26Sn7KY2mVYm2mBcmUA3Ci4kB5mxccHXYpSB', 'AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),  # noqa: E501
            ('solana_token_account_JCqbv7r3mtYhzruNFjc21X14fndDVBLMiaNQrsHVpWui', '2YM8LrJGRtsDcWeqsjX2EQwJfhArxyDdtDzgt7vrwwbV,6mJqqT5TMgveDvxzBt3hrjGkPV5VAj7tacxFCT3GebXh'),  # noqa: E501
        ]
