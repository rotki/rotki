# Stacks Blockchain Integration PRD

**Document Version**: 1.0
**Date**: 2025-01-24
**Status**: Draft - Awaiting Expert Review
**Target Branch**: `develop`

---

## Executive Summary

This document outlines the plan to add first-class Stacks blockchain support to rotki, a privacy-focused crypto portfolio management and tax reporting application. The integration will enable users to track STX holdings, SIP-10 tokens (including sBTC), transaction history, and protocol interactions for tax preparation and portfolio analysis.

---

## 1. Project Goals

### Primary Objectives
1. **Native STX tracking** - Balance queries and transaction history for Stacks addresses
2. **SIP-10 token support** - sBTC, stSTX, stSTXBTC, and other fungible tokens
3. **Transaction decoding** - Human-readable interpretation of Stacks transactions
4. **Protocol support** - sBTC bridge, stacking, liquid staking (LISA)
5. **Tax preparation** - Accurate cost basis and gain/loss calculations

### Success Criteria
- Users can add Stacks addresses and see balances
- Transaction history is fetched and stored
- Key protocol interactions (sBTC pegin/pegout, stacking) are decoded with human-readable descriptions
- Events integrate with rotki's existing accounting engine

---

## 2. Current State Analysis

### 2.1 Rotki Architecture Overview

Rotki is a multi-chain portfolio tracker with:
- **Python backend** (Flask API, SQLite database, accounting engine)
- **Vue.js/TypeScript frontend** (Electron desktop + web)
- **Rust service** (Colibri - performance components)

The backend manages blockchain integrations through a `ChainsAggregator` that instantiates chain-specific managers.

### 2.2 Existing Chain Support Tiers

Our code analysis identified 5 tiers of chain support:

| Tier | Chains | Features |
|------|--------|----------|
| **1** | Ethereum | 78+ protocol decoders, full accounting, module system |
| **2** | Arbitrum, Optimism, Base, Polygon, etc. | EVM inheritance, 10-60 protocol decoders each |
| **3** | Solana | Custom decoder, 3 protocol modules, no accounting aggregator |
| **4** | Bitcoin, Bitcoin Cash | UTXO model, external APIs, no decoding |
| **5** | Polkadot, Kusama | Balance tracking only |

### 2.3 Current Stacks Support

**None.** Zero existing Stacks code in the repository:
- No `SupportedBlockchain.STACKS` enum entry
- No `rotkehlchen/chain/stacks/` directory
- No Stacks-related types or configurations

This is a greenfield implementation.

### 2.4 Reference Implementation: Solana

Solana (Tier 3) is the closest architectural match for Stacks because:
- Non-EVM chain with custom address format
- Has transaction decoding (unlike Bitcoin)
- Limited protocol coverage (3 modules vs Ethereum's 78+)
- No accounting aggregator (uses default rules)

**Solana structure** (our template):
```
rotkehlchen/chain/solana/
├── __init__.py
├── manager.py              # SolanaManager
├── node_inquirer.py        # RPC interface
├── transactions.py         # TX fetching/storage
├── validation.py           # Address validation
├── constants.py
├── types.py
├── utils.py
└── decoding/
    ├── decoder.py          # SolanaTransactionDecoder
    ├── tools.py            # Decoder utilities
    ├── constants.py
    └── structures.py
└── modules/
    ├── jito/
    ├── jupiter/
    └── pump_fun/
```

---

## 3. Technical Findings

### 3.1 Type System Integration Points

From `rotkehlchen/types.py`, we need to add Stacks to:

```python
# New type
StacksAddress = NewType('StacksAddress', str)

# Add to enums/unions
SupportedBlockchain.STACKS
BlockchainAddress  # Union type including StacksAddress
CHAINS_WITH_CHAIN_MANAGER
CHAINS_WITH_TRANSACTIONS
CHAINS_WITH_TX_DECODING
CHAINS_WITH_TRANSACTION_DECODERS

# New location
Location.STACKS = <next_available_int>
```

### 3.2 Chain Manager Pattern

All chain managers follow this hierarchy:
```
ChainManager (abstract)
└── ChainManagerWithTransactions[StacksAddress]
    └── ChainManagerWithNodesMixin[StacksInquirer]
        └── StacksManager
```

Required implementations:
- `query_balances()` - Native STX + SIP-10 tokens
- Account tracking integration
- Transaction fetching coordination

### 3.3 Node Inquirer Pattern

The `StacksInquirer` needs to wrap Stacks API calls:

**Data Sources**:
- **Hiro API** (hosted): `https://api.mainnet.hiro.so`
- **Self-hosted node**: For full decentralization

**Key Endpoints**:
| Endpoint | Purpose |
|----------|---------|
| `/extended/v1/address/{addr}/balances` | STX + token balances |
| `/extended/v1/address/{addr}/transactions` | Transaction history |
| `/extended/v2/transactions/{txid}` | Transaction details |
| `/v2/contracts/call-read/{contract}/{function}` | Contract reads |

### 3.4 Transaction Decoder Architecture

Stacks transactions contain:
- **Transaction type**: token_transfer, contract_call, smart_contract, etc.
- **Contract calls**: `contract_id`, `function_name`, `function_args`
- **Events**: STX transfers, FT transfers, NFT events, print events

The decoder maps these to `HistoryBaseEntry` events with:
- `event_type` / `event_subtype` (DEPOSIT, WITHDRAWAL, TRADE, etc.)
- `counterparty` (protocol identifier like `CPT_SBTC`)
- `notes` (human-readable description)

### 3.5 Protocol Module Candidates

Based on Stacks ecosystem analysis:

| Protocol | Priority | Complexity | Description |
|----------|----------|------------|-------------|
| **sBTC Bridge** | P0 | Medium | BTC<->sBTC pegin/pegout |
| **Native Stacking** | P0 | Medium | STX stacking for rewards |
| **LISA (stSTX)** | P1 | Medium | Liquid staking protocol |
| **Velar DEX** | P2 | Low | AMM swaps |
| **Alex DEX** | P2 | Low | AMM swaps |
| **STX20 tokens** | P2 | Low | Token standard |

---

## 4. Proposed Architecture

### 4.1 Directory Structure

```
rotkehlchen/chain/stacks/
├── __init__.py
├── manager.py                 # StacksManager
├── node_inquirer.py           # StacksInquirer (Hiro API wrapper)
├── transactions.py            # StacksTransactions
├── validation.py              # Address validation (SP/ST prefix)
├── constants.py               # Chain constants
├── types.py                   # Stacks-specific types
├── utils.py                   # Utility functions
├── tokens.py                  # SIP-10 token handling
└── decoding/
    ├── __init__.py
    ├── decoder.py             # StacksTransactionDecoder
    ├── interfaces.py          # Decoder interface for modules
    ├── constants.py           # Decoding constants
    └── structures.py          # Context/output types
└── modules/
    ├── __init__.py
    ├── sbtc/                  # sBTC bridge
    │   ├── __init__.py
    │   ├── decoder.py
    │   └── constants.py
    ├── stacking/              # Native stacking
    │   ├── __init__.py
    │   ├── decoder.py
    │   └── constants.py
    └── lisa/                  # Liquid staking
        ├── __init__.py
        ├── decoder.py
        └── constants.py
```

### 4.2 Implementation Phases

#### Phase 1: Foundation (MVP)
**Goal**: Users can add Stacks addresses and see balances

- [ ] Type registration (`types.py` additions)
- [ ] Address validation (SP/ST prefix, checksum)
- [ ] `StacksManager` skeleton
- [ ] `StacksInquirer` with balance endpoints
- [ ] STX native balance tracking
- [ ] Integration with `ChainsAggregator`
- [ ] Frontend: Add Stacks to chain selector

**Deliverable**: Basic balance tracking, no transactions

#### Phase 2: Transaction History
**Goal**: Fetch and store transaction history

- [ ] `StacksTransactions` class
- [ ] Transaction fetching from Hiro API
- [ ] Database schema for Stacks transactions
- [ ] Basic transaction display (no decoding)
- [ ] SIP-10 token balance tracking

**Deliverable**: Full transaction history, token balances

#### Phase 3: Transaction Decoding
**Goal**: Human-readable transaction interpretation

- [ ] `StacksTransactionDecoder` base implementation
- [ ] Decode STX transfers
- [ ] Decode SIP-10 token transfers
- [ ] Generic contract call decoding
- [ ] Event creation with proper types/subtypes

**Deliverable**: Decoded transactions with descriptions

#### Phase 4: Protocol Modules
**Goal**: Protocol-specific decoding for DeFi

- [ ] sBTC bridge decoder (pegin/pegout)
- [ ] Native stacking decoder
- [ ] LISA liquid staking decoder
- [ ] Counterparty constants (`CPT_SBTC`, `CPT_STACKING`, etc.)

**Deliverable**: Full protocol support for core Stacks DeFi

#### Phase 5: Polish & Testing
**Goal**: Production readiness

- [ ] Comprehensive test suite
- [ ] Error handling hardening
- [ ] Rate limiting for API calls
- [ ] Documentation
- [ ] Performance optimization

---

## 5. Key Design Decisions

### 5.1 API Strategy

**Recommendation**: Start with Hiro API, abstract for future node support

```python
class StacksInquirer:
    def __init__(self, api_url: str = 'https://api.mainnet.hiro.so'):
        self.api_url = api_url

    # All methods use self.api_url, easily swappable to self-hosted node
```

**Rationale**: Hiro API is reliable and well-documented. Self-hosted node support can be added later without architectural changes.

### 5.2 Transaction Decoding Approach

**Recommendation**: Contract-call pattern matching (like Solana)

1. Parse transaction to extract `contract_id` and `function_name`
2. Route to protocol-specific decoder based on contract address
3. Fallback to generic decoder for unknown contracts

**Rationale**: Stacks contract calls are explicit (unlike EVM event logs), making pattern matching straightforward.

### 5.3 Token Handling

**Recommendation**: Create `StacksToken` model similar to `SolanaToken`

- SIP-10 tokens have `contract_id::token_name` format
- Store in global assets database with `STACKS` chain
- Support for both well-known tokens and user-added custom tokens

### 5.4 sBTC Bridge Integration

**Challenge**: sBTC pegin originates on Bitcoin, pegout originates on Stacks

**Recommendation**:
- Track Stacks-side events only initially
- Correlate with Bitcoin transactions via sBTC deposit/withdrawal addresses if Bitcoin integration exists
- Use `HistoryEventType.DEPOSIT/WITHDRAWAL` + `HistoryEventSubType.BRIDGE` pattern (matches Arbitrum/Optimism bridges)

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Hiro API rate limits | Medium | Medium | Implement caching, respect rate limits |
| Stacks API changes | Low | High | Version pin API calls, monitor changelogs |
| Complex contract decoding | Medium | Medium | Start with known protocols, generic fallback |
| sBTC bridge complexity | Medium | Medium | Phase 4 scope, can ship without it |
| Testnet differences | Low | Low | Test against mainnet data |

---

## 7. Open Questions for Review

### Architecture Questions

1. **Tier Selection**: We're targeting Tier 3 (Solana-like). Should we plan for Tier 2 features (accounting aggregator, module activation) from the start, or add later?

2. **API Abstraction**: Should `StacksInquirer` support multiple backends (Hiro, self-hosted node) in Phase 1, or defer to later?

3. **Cross-chain Correlation**: For sBTC bridge events, how should we handle correlation with Bitcoin-side transactions? Same approach as Arbitrum/Ethereum bridge correlation?

### Scope Questions

4. **Token Priority**: Should we support all SIP-10 tokens from Phase 2, or start with a curated list (sBTC, stSTX, etc.)?

5. **NFT Support**: SIP-009 NFTs exist on Stacks. Include in scope or defer?

6. **Mempool Tracking**: Should we show pending transactions, or only confirmed?

### Implementation Questions

7. **Solana Parity**: The Solana implementation has 3 protocol modules. For Stacks, should we target similar coverage (sBTC, stacking, LISA) or more/fewer?

8. **Testing Strategy**: Solana tests use mocked data. Should we follow the same pattern, or use VCR recordings for Stacks API calls?

9. **Frontend Changes**: What UI changes are needed beyond adding Stacks to the chain selector? Token icons? Protocol-specific views?

---

## 8. Appendices

### A. Stacks Address Format

- **Mainnet**: Starts with `SP` (e.g., `SP2J6ZY48GV1EZ5V2V5RB9MP66SW86PYKKNRV9EJ7`)
- **Testnet**: Starts with `ST` (e.g., `ST2J6ZY48GV1EZ5V2V5RB9MP66SW86PYKKNRVF5T9`)
- **Format**: c32check encoding of version byte + hash160

### B. Key Stacks Contracts

| Protocol | Contract ID | Purpose |
|----------|-------------|---------|
| sBTC | `SP3K8BC0PPEVCV7NZ6QSRWPQ2JE9E5B6N3PA0KBR9.sbtc-token` | sBTC token |
| sBTC Bridge | `SP3K8BC0PPEVCV7NZ6QSRWPQ2JE9E5B6N3PA0KBR9.sbtc-registry` | Bridge registry |
| Stacking | `SP000000000000000000002Q6VF78.pox-4` | PoX stacking |
| LISA stSTX | `SM3KNVZS30WM7F89SXKVVFY4SN9RMPZZ9FX929N0V.ststx-token` | Liquid staking |

### C. Hiro API Rate Limits

- **Free tier**: 50 requests/minute
- **Authenticated**: 500 requests/minute
- **Recommendation**: Implement exponential backoff and caching

### D. Related PRs/Issues

- Solana implementation: Reference for non-EVM chain addition
- Bridge decoder patterns: `rotkehlchen/chain/evm/decoding/utils.py`

---

## 9. Feedback Requested

Please review and provide feedback on:

1. **Accuracy of analysis** - Did we correctly understand rotki's architecture and the Solana reference implementation?

2. **Approach validation** - Is Tier 3 (Solana-like) the right target? Any concerns with the proposed architecture?

3. **Phase breakdown** - Does the phased approach make sense? Should phases be combined or split differently?

4. **Scope concerns** - Is the scope appropriate for an initial integration? Too ambitious? Missing critical features?

5. **Technical risks** - Any risks we haven't identified? Concerns about specific design decisions?

6. **Timeline expectations** - Given the scope, what timeline expectations should we set?

---

*This document was prepared based on static code analysis of the rotki codebase. Implementation details may need adjustment based on runtime testing and API behavior.*
