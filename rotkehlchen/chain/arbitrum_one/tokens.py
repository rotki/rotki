from rotkehlchen.chain.evm.tokens import ARBISCAN_MAX_ARGUMENTS_TO_CONTRACT, EvmTokens


class ArbitrumOneTokens(EvmTokens):
    INDEXER_CHUNK_SIZE = ARBISCAN_MAX_ARGUMENTS_TO_CONTRACT
