# Stacks Blockchain Integration PRD

**Document Version**: 1.1
**Date**: 2025-01-24
**Status**: Reviewed - Incorporating Feedback
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
- **Self-hosted node**: For full decentralization (deferred)

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

**Type System & Registration**:
- [ ] Add `StacksAddress = NewType('StacksAddress', str)` to `types.py`
- [ ] Add `SupportedBlockchain.STACKS` enum entry
- [ ] Add `Location.STACKS` with next available int
- [ ] Extend unions: `CHAINS_WITH_TRANSACTIONS`, `CHAINS_WITH_TX_DECODING`, `CHAINS_WITH_TRANSACTION_DECODERS`, `CHAINS_WITH_CHAIN_MANAGER`
- [ ] Update `BlockchainAddress` union type

**Core Implementation**:
- [ ] Address validation (SP/ST prefix, c32check)
- [ ] `StacksManager` skeleton
- [ ] `StacksInquirer` with balance endpoints
- [ ] STX native balance tracking

**Aggregator Wiring** (critical - do early):
- [ ] Add `stacks_manager` to `ChainsAggregator.__init__`
- [ ] Add `self.stacks` attribute and `stacks_lock`
- [ ] Update `rotkehlchen/rotkehlchen.py` manager instantiation
- [ ] Audit and update ALL code using `CHAINS_WITH_*` tuples
- [ ] Update REST API schemas to surface Stacks
- [ ] Update test fixtures

**Frontend**:
- [ ] Add Stacks to chain selector
- [ ] Add STX icon (verify icon mapping)
- [ ] Address validation hints (SP/ST prefix)
- [ ] Verify TypeScript strict mode passes

**Deliverable**: Basic balance tracking, no transactions

#### Phase 2: Transaction History
**Goal**: Fetch and store transaction history

**Data Layer**:
- [ ] `StacksTransactions` class
- [ ] Database schema (`DBStacksTx` mirroring `DBSolanaTx`)
- [ ] DB migrations (coordinate with CI)
- [ ] "Not decoded" query support
- [ ] Paging, deduplication, "existing tx" filtering

**API Integration**:
- [ ] Transaction fetching from Hiro API
- [ ] **Rate limiting with exponential backoff** (implement early)
- [ ] **Response caching** (implement early)
- [ ] Batch requests where possible

**Token Support**:
- [ ] `StacksToken` model for SIP-10 tokens
- [ ] Token metadata caching (decimals, symbol, name)
- [ ] Curated allowlist: sBTC, stSTX, stSTXBTC, core tokens
- [ ] `get_or_create_stacks_token()` with tolerant defaults for unknown tokens
- [ ] Lazy token creation for tokens discovered during decoding

**Data Integrity**:
- [ ] Only persist anchored/confirmed transactions (no microblocks)
- [ ] Normalize all timestamps to `TimestampMS` on ingestion

**Deliverable**: Full transaction history, token balances

#### Phase 3: Transaction Decoding
**Goal**: Human-readable transaction interpretation

**Base Decoder**:
- [ ] `StacksTransactionDecoder` base implementation
- [ ] Decode STX transfers → `DEPOSIT/WITHDRAWAL`
- [ ] Decode SIP-10 token transfers → `DEPOSIT/WITHDRAWAL`
- [ ] Generic contract call decoding (fallback)

**Event Creation**:
- [ ] Define counterparty constants (`CPT_SBTC`, `CPT_STACKING`, `CPT_LISA`)
- [ ] Consistent `event_type`/`event_subtype` usage
- [ ] Human-readable notes generation
- [ ] Proper `sequence_index` ordering

**Deliverable**: Decoded transactions with descriptions

#### Phase 4: Protocol Modules
**Goal**: Protocol-specific decoding for DeFi

**Shared Infrastructure**:
- [ ] Bridge utility for standardized `DEPOSIT/WITHDRAWAL + BRIDGE` semantics
- [ ] Shared notes formatting for bridge events

**sBTC Bridge** (P0):
- [ ] Decode pegin events (BTC → sBTC)
- [ ] Decode pegout events (sBTC → BTC)
- [ ] Standalone events (no cross-chain correlation in v1)
- [ ] Optional `related_tx` field for future BTC correlation

**Native Stacking** (P0):
- [ ] Decode stack-stx calls
- [ ] Decode stacking rewards → `REWARD` with `CPT_STACKING`
- [ ] Decode unlock events

**LISA Liquid Staking** (P1):
- [ ] Decode stSTX mint/burn
- [ ] Decode staking rewards

**Deliverable**: Full protocol support for core Stacks DeFi

#### Phase 5: Polish & Testing
**Goal**: Production readiness

**Testing**:
- [ ] Comprehensive test suite with mocked data (no VCR)
- [ ] Deterministic fixtures from real Hiro API samples
- [ ] Verify decoding + DB persistence
- [ ] Integration tests for full flow

**Hardening**:
- [ ] Error handling review
- [ ] Edge case coverage (empty responses, malformed data)
- [ ] Logging completeness

**Documentation**:
- [ ] Developer documentation
- [ ] API endpoint documentation

**Performance**:
- [ ] Query optimization
- [ ] Caching effectiveness review

**Deliverable**: Production-ready Stacks integration

---

## 5. Key Design Decisions

### 5.1 API Strategy

**Decision**: Hiro API only in Phase 1, with swappable interface

```python
class StacksInquirer:
    def __init__(self, api_url: str = 'https://api.mainnet.hiro.so'):
        self.api_url = api_url
        # All methods use self.api_url, easily swappable later
```

**Rationale**: Hiro API is reliable and well-documented. Interface abstraction allows adding self-hosted node support later without architectural changes.

### 5.2 Transaction Decoding Approach

**Decision**: Contract-call pattern matching (like Solana)

1. Parse transaction to extract `contract_id` and `function_name`
2. Route to protocol-specific decoder based on contract address
3. Fallback to generic decoder for unknown contracts

**Rationale**: Stacks contract calls are explicit (unlike EVM event logs), making pattern matching straightforward.

### 5.3 Token Handling

**Decision**: Curated allowlist + lazy creation with tolerant defaults

- **Allowlist** (known at build time): sBTC, stSTX, stSTXBTC, core SIP-10 tokens
- **Lazy creation**: Tokens discovered during tx decoding get created on-demand
- **Tolerant defaults**: Handle incomplete SIP-10 metadata gracefully
- **Metadata caching**: Cache decimals/symbol/name, fall back to contract reads

```python
KNOWN_STACKS_TOKENS: Final = {
    'SP3K8BC0PPEVCV7NZ6QSRWPQ2JE9E5B6N3PA0KBR9.sbtc-token::sbtc': {...},
    'SM3KNVZS30WM7F89SXKVVFY4SN9RMPZZ9FX929N0V.ststx-token::ststx': {...},
    # ...
}

def get_or_create_stacks_token(contract_id: str) -> Asset:
    # Check known tokens first, then create with defaults
```

### 5.4 sBTC Bridge Integration

**Decision**: Standalone Stacks-side events, defer cross-chain correlation

- Emit `DEPOSIT/WITHDRAWAL` + `BRIDGE` subtype for bridge events
- Events are complete and meaningful on their own
- Optional `related_tx` field prepared for future BTC correlation
- Cross-chain auto-pairing deferred to post-v1

**Rationale**: Cross-chain correlation is complex. Ensuring Stacks-side events stand alone cleanly is more valuable than incomplete pairing.

### 5.5 Event Type Semantics

**Decision**: Follow established patterns

| Operation | event_type | event_subtype | counterparty |
|-----------|------------|---------------|--------------|
| STX transfer in | `DEPOSIT` | `NONE` | - |
| STX transfer out | `WITHDRAWAL` | `NONE` | - |
| Token transfer in | `DEPOSIT` | `NONE` | - |
| Token transfer out | `WITHDRAWAL` | `NONE` | - |
| Bridge deposit | `DEPOSIT` | `BRIDGE` | `CPT_SBTC` |
| Bridge withdrawal | `WITHDRAWAL` | `BRIDGE` | `CPT_SBTC` |
| Stacking reward | `STAKING` | `REWARD` | `CPT_STACKING` |

### 5.6 Transaction Confirmation

**Decision**: Anchored transactions only

- Only persist transactions in anchor blocks (confirmed)
- Do not track microblock/pending transactions
- Avoids UX confusion from reorgs

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Hiro API rate limits** | Medium | Medium | Implement backoff + caching from Phase 2 |
| **Aggregator ripple effect** | High | Medium | Audit all `CHAINS_WITH_*` usage in Phase 1 |
| **DB schema/migrations** | Medium | Medium | Mirror `DBSolanaTx` pattern, coordinate with CI |
| **Microblock confusion** | Medium | Low | Only persist anchored transactions |
| **Timestamp mismatches** | Medium | High | Normalize to `TimestampMS` on ingestion |
| **Incomplete token metadata** | High | Low | Tolerant defaults + caching + lazy reads |
| **Stacks API changes** | Low | High | Version pin API calls, monitor changelogs |
| **Complex contract decoding** | Medium | Medium | Start with known protocols, generic fallback |
| **sBTC bridge complexity** | Medium | Medium | Standalone events, defer correlation |
| **Frontend type errors** | Medium | Low | Verify strict mode passes in Phase 1 |

---

## 7. Decisions Made (Post-Review)

Based on technical review feedback, the following questions have been resolved:

| Question | Decision |
|----------|----------|
| **Tier selection** | Tier 3 for v1; add Tier 2 features (accounting aggregator) post-stability |
| **API abstraction** | Hiro-only in Phase 1; keep interface swappable |
| **Cross-chain correlation** | Emit standalone events; defer auto-pairing |
| **Token priority** | Curated allowlist + lazy creation for others |
| **NFT support** | Defer; not critical for tax/value scope |
| **Mempool tracking** | Confirmed/anchored only; pending deferred |
| **Protocol coverage** | Target 3 modules (sBTC, stacking, LISA); DEXes are P2 |
| **Testing strategy** | Mocked tests (no VCR); deterministic fixtures from real samples |
| **Frontend changes** | Chain selector + icons + address hints; existing history UI suffices |

---

## 8. Implementation Notes

### 8.1 Code Touchpoints for Phase 1

**Type Registration** (`rotkehlchen/types.py`):
- Add `StacksAddress` NewType
- Add to `SupportedBlockchain` enum
- Add to `Location` enum
- Extend: `CHAINS_WITH_TRANSACTIONS`, `CHAINS_WITH_TX_DECODING`, `CHAINS_WITH_TRANSACTION_DECODERS`, `CHAINS_WITH_CHAIN_MANAGER`

**Manager Wiring**:
- `rotkehlchen/rotkehlchen.py` - Manager instantiation
- `rotkehlchen/chain/aggregator.py` - `ChainsAggregator` constructor, attributes, locks
- Test fixtures using chain managers
- REST API schemas surfacing chain lists

**New Package**:
- `rotkehlchen/chain/stacks/__init__.py`
- `rotkehlchen/chain/stacks/manager.py`
- `rotkehlchen/chain/stacks/node_inquirer.py`
- `rotkehlchen/chain/stacks/validation.py`
- `rotkehlchen/chain/stacks/constants.py`
- `rotkehlchen/chain/stacks/types.py`

### 8.2 Database Schema (Phase 2)

Mirror `DBSolanaTx` pattern:
- Stacks transactions table
- "Not decoded" query support
- Deduplication on tx hash
- Filtering by address/block range

### 8.3 Event Semantics Reference

```python
# STX/Token transfers
HistoryEventType.DEPOSIT / WITHDRAWAL
HistoryEventSubType.NONE

# Bridge operations
HistoryEventType.DEPOSIT / WITHDRAWAL
HistoryEventSubType.BRIDGE
counterparty = CPT_SBTC

# Stacking rewards
HistoryEventType.STAKING
HistoryEventSubType.REWARD
counterparty = CPT_STACKING
```

---

## 9. Appendices

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
- **Mitigation**: Exponential backoff + response caching (Phase 2)

### D. Related Code References

- Solana implementation: `rotkehlchen/chain/solana/`
- Bridge decoder patterns: `rotkehlchen/chain/evm/decoding/utils.py`
- Type unions: `rotkehlchen/types.py` lines 609-733

---

## 10. Changelog

### v1.1 (2025-01-24)
- Incorporated technical review feedback
- Moved rate limiting/caching from Phase 5 to Phase 2
- Added aggregator wiring audit to Phase 1
- Clarified token strategy (curated allowlist + lazy creation)
- Added microblock/confirmation handling decision
- Added timestamp normalization requirement
- Expanded risk assessment with new items
- Added "Decisions Made" section with resolved questions
- Added implementation notes with specific code touchpoints

### v1.0 (2025-01-24)
- Initial draft

---

*This document was prepared based on static code analysis of the rotki codebase and technical review feedback. Implementation details may need adjustment based on runtime testing and API behavior.*
