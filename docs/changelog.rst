=========
Changelog
=========

* :feature:`-` rotki decodes transactions and detects balances related to Blur staking.
* :feature:`1633` rotki now supports AAVE staking.
* :feature:`7568` Eigenlayer native restaking events are now properly decoded and balances in native restaking eigenpods or the delayed withdrawal system are automatically detected.
* :feature:`6115` Now free users can filter history events too.
* :feature:`7570` Users can choose whether to automatically force-push when a time discrepancy warning occurs during automatic database sync.
* :feature:`-` Degen airdrop 2 season 3 claim event should now be properly decoded in the history events view.
* :feature:`-` The eigenlayer airdrop claim event should now be properly decoded in the history events view.
* :feature:`7358` Added support for detection of staked GRT tokens on Arbitrum.
* :bug:`-` Fix the issue where the MATIC amount always shows as zero in the Polygon balance table.
* :bug:`7915` Show OKX balances locked in active trades.
* :feature:`-` rotki now optionally can use the decentralized TheGraph service. You can get a free api key at https://thegraph.com/studio/apikeys/
* :feature:`7816` rotki should now support the new coinbase api key format from the coinbase develop portal.
* :bug:`-` Compound v2 transactions containing also flash loans of same asset type will now be properly decoded.

* :release:`1.33.0 <2024-05-08>`
* :feature:`7798` rotki now accurately decodes transactions on the Kyber swap aggregator across all supported chains.
* :feature:`-` Users will now be able to delete transactions and the associated events in history events.
* :feature:`7074` rotki provides a calendar view where users can add and track events related to their activities. Users can also set reminders to perform actions associated with these events.
* :feature:`-` Claiming the harvest finance hack compensation grain airdrop will be properly shown as airdrop claim in the history events.
* :feature:`-` Claiming the pickle finance hack compensation cornichon airdrop will be properly shown as airdrop claim in the history events.
* :feature:`-` Omni airdrop claims are properly decoded and omni airdrop eligibility is shown in rotki's airdrop list.
* :feature:`7084` Compound v3 events will now get decoded and its assets and liabilities will be shown on the dashboard properly.
* :feature:`-` Users will now be able to navigate the page (go back or forward) using the keyboard shortcuts "Cmd + Left Arrow" or "Cmd + Right Arrow".
* :feature:`3617` ZKSync lite is now supported as a chain. Balances are detected and history of the activity of all your tracked addresses for zksync lite will now be visible in the history events section.
* :feature:`-` fluence dev rewards airdrop claim events will now be properly decoded in the history events.
* :feature:`-` rotki will now properly decode the transactions for bridging to and from Scroll.
* :feature:`7708` rotki now properly decodes all native to/from wrapped token transactions (e.g. ETH<->WETH, Matic<->WMatic) on all supported EVM chains
* :feature:`6636` Aave v3 positions and liabilities will now be properly shown in the dashboard.
* :feature:`7423` Users will be able to sort address book entries by displayed name and address.
* :feature:`7086` Added support for GMX v1 in Arbitrum.
* :feature:`7281` rotki will now properly decode the transactions done on Aave v2 and v3 on all the supported chains.
* :feature:`2698` Users can now manually link assets on their exchanges to assets recognized by Rotki, without having to wait for a new release.
* :feature:`-` rotki will now properly decode the Uniswap V3 events on other supported chains.
* :feature:`5978` rotki will now properly decode the swaps done via the 0x protocol.
* :feature:`-` The claim event of the Degen airdrop 2 will be correctly decoded.
* :bug:`-` Binance balances will now include funding wallet's balances.
* :feature:`-` rotki now supports Coinbase transactions using Advanced Trading.
* :bug:`-` Velodrome and Aerodrome LP pools will now refresh properly.
* :bug:`-` Fix a bug where the custom price is not applied in the balance view under the account table.
* :bug:`-` Deleting an EVM RPC node will no longer fail sometimes with a "Can't delete etherscan node" error. Additionally non-mainnet etherscan nodes are no longer deletable.
* :bug:`-` Nigerian Naira should be correctly detected in binance.
* :bug:`-` Kraken balances in new yield-bearing products and automatic staking for new kraken users should now appear properly.

* :release:`1.32.2 <2024-03-15>`
* :bug:`7531` rotki will now prioritize manual prices above other price oracles and calculations.
* :bug:`-` rotki will display NFT prices correctly across all asset types.
* :bug:`7572` Fix issue where coinbase data query could result in an error popup.
* :bug:`7611` USDT balances and trades in bitcoin.de should now work properly.
* :bug:`-` Sending money to SEPA or bridging with the BurnFrom monerium signature will now be properly decoded by rotki.
* :bug:`-` Fix issue where long label in manual balances breaks the alignment of chain names.
* :bug:`-` If saving a setting fails, error messages will no longer disappear automatically.
* :bug:`7532` Curve LP token price calculation should now be correct.
* :bug:`-` All the curve pools in ethereum should be queried again.

* :release:`1.32.1 <2024-02-23>`
* :bug:`-` rotki will now automatically update the local airdrops' CSVs when needed, without manually deleting them.
* :bug:`-` Fix the issue where an incorrect amount of ETH is displayed in the Loopring account table.
* :bug:`-` Binance lending positions and rewards will get properly decoded and displayed again.
* :bug:`7488` Show tags in multi-lines when multiple to avoid horizontal scroll.
* :bug:`7497` In ETH staking view execution rewards should now be counted properly. MEV reward and block reward should not both be counted if recipient is not tracked.
* :bug:`7522` Invalid ENS names shouldn't stop the decoding process anymore.
* :bug:`-` Removing an address from one of the EVM chains won't affect the decoded events in other chains anymore.
* :bug:`-` ETH withdrawal events should now be taxable again if the setting for their treatment after withdrawals enabled is on (which is by default).
* :bug:`-` Invalid data in airdrops' CSVs or JSONs will now get ignored to show the rest of the valid data.

* :release:`1.32.0 <2024-02-16>`
* :feature:`7383` rotki will now update airdrops' data remotely without needing to update the app.
* :bug:`7435` Fix the issue where, in rare cases, users receive a JavaScript error popup when minimizing the window.
* :feature:`7357` rotki will now properly detect and decode Shutter token airdrop and delegation.
* :feature:`-` Transactions contributing to Juicebox campaigns, such as the Free Alexey and Roman from Tornado, are now properly decoded.
* :feature:`-` Octant epoch reward claiming transactions are now properly decoded.
* :feature:`6460` rotki will now properly import the trades from the CSVs that are exported from Kucoin.
* :feature:`7018` rotki will now save the labels for a blockchain account in the address book. If a name is already present in the address book for that blockchain account, Name Priority setting in 'Frontend-only Settings' section is used to determine which one to keep. Addressbook is prioritized by default.
* :feature:`-` rotki is now available in French.
* :feature:`-` Tokens deposited in EigenLayer will now be tracked.
* :feature:`-` Aerodrome transactions in BASE will now be properly supported.
* :feature:`-` Notes for governance votes will include the reasoning if it was provided in the transaction when voting on-chain.
* :feature:`7214` Swaps done through Paraswap Augustus on Ethereum, Arbitrum, Optimism, Polygon, and Base chains, will now get properly decoded in the history view and will be taken into account during accounting.
* :feature:`7027` Monerium transactions are now decoded as mints and burns. If the user provides monerium credentials then a periodic task pulls data from the monerium API and the transactions are enriched with actual banking data and/or with bridging data from chain to chain.
* :feature:`7176` The exported CSV for PnL Report now contains a label of the address in notes, if available.
* :feature:`7146` The exported CSV for PnL Report now contains an Asset column with symbols.
* :feature:`6254` Users can now stop the execution of long-running queries.
* :feature:`7092` Users of metamask swaps will now see them properly decoded in the history view and have them taken into account during accounting.
* :feature:`-`  Bridging transactions across all EVM chains done via socket will now be decoded properly.
* :feature:`7051` Users will be able to add a custom price directly from the asset overview page.
* :feature:`-` Arbitrum's governance votes should now be decoded properly.
* :feature:`4841` The rotki data directory is now more organized.
* :feature:`-` Transactions that have interacted with the WXDAI contract are now properly decoded.
* :feature:`1574` Interactions with the ygov.finance contract are now decoded.
* :bug:`7276` Fix the issue where Uniswap v3 positions are counted twice for the net worth.
* :bug:`7147` rotki should no longer query price multiple times for the same asset across different chains.
* :bug:`-`  Whether an airdrop has been claimed or not will be properly detected again for the supported airdrops.
* :feature:`7399` Transactions involving the Savings xDAI contract at gnosis will now be properly decoded.
* :bug:`-` Incorrectly processed kraken events should no longer occur.
* :bug:`-` It should no longer be possible to merge the same asset to itself, thus botching the asset in your database.
* :feature:`-` Transactions burning vested vCOW to claim COW tokens will now be properly decoded for both gnosis chain and ethereum mainnet.
* :bug:`-` Fix an issue where kraken instant swaps could have an invalid type for fee events.
* :bug:`-` Querying coinbase data should no longer show 404 error if the user has too many accounts and tries to query trades or deposits/withdrawals.

* :release:`1.31.3 <2024-01-31>`
* :bug:`-` The history events section will have correct pagination for free users, with all the events showing correct sub-events.
* :bug:`7359` NFTs should be queried and displayed properly again.
* :bug:`7362` Filtering by customized events in the free version should work fine again.
* :bug:`-` Premium sync failure will now appear in the toolbar indicator instead of showing a notification.
* :bug:`-` Importing sell trades via rotki generic trades CSV import will now work properly again.
* :bug:`-` All Gnosis bridge dai events from ethereum to gnosis chain should now be decoded properly.
* :bug:`7526` Liquity trove LUSD borrowing fee and stability pool LQTY frontend fee will now be properly shown and processed by rotki.
* :bug:`-` USDT will be processed correctly when importing events from nexo.
* :bug:`-` Failure to resolve etherscan api or hitting maximum backoff after too many retries will now no longer raise an exception.
* :bug:`-` Some coinbase trades imported via the API should no longer show negative amounts. If you see negative amounts, purge and repull coinbase data.
* :bug:`-` The defillama oracle should now work correctly with tokens in arbitrum and binance.
* :bug:`-` Removing exchanges will also remove them from the setting of non syncing exchanges.

* :release:`1.31.2 <2023-12-22>`
* :bug:`-` Importing timestamp in CSV in scientific format should now work without errors.
* :bug:`7123` Adding an EVM EOA address that has only withdrawals/blocks activity will no longer fail.
* :bug:`7082` Now disabling sync for an exchange instance won't prevent other instances in the same exchange from querying new trades.
* :bug:`7071` Fix the issue where users on mobile devices need to scroll to login.
* :bug:`7120` Fix the issue where after removing an exchange key, an error notification is shown.
* :bug:`7115` Fix the issue with decimal point for amount input.
* :bug:`7119` Removed bittrex as an exchanged added via api key since it has shut down. But users can now import bittrex CSVs in order to get their history into rotki.
* :bug:`-` Bitmex history queries should now work properly again after Bitmex changed their API without versioning.
* :bug:`1863` Bitstamp deposit/withdrawals should now also show the address and transaction id.
* :bug:`7075` Coinbase api should now be usable again. Additionally history retrieval speed has improved by orders of magnitude.
* :bug:`-` Fix the issue where user profiles on the login screen are empty after logging out.
* :bug:`-` Now users will be able to see the most recent assets without restarting the app when filtering by owned assets in the assets view.
* :bug:`-` Withdrawal events for ethereum staking will now respect accounting rules.
* :bug:`7059` Fix the issue where adding an account via MetaMask is not working.
* :bug:`7057` Fix the issue where the app restarts when the file upload button is clicked.
* :bug:`-` rotki should no longer try mainnet uniswap onchain price queries for other evm tokens and errors should be handled better

* :release:`1.31.1 <2023-12-06>`
* :bug:`-` Fix the bug that causes the error screen to appear strangely in dark mode.
* :bug:`7012` Fix issue where the title for the statistics card are missing.
* :bug:`7039` The edge case of a failed eth_call during initialization of decoders will no longer crash the user login task.
* :bug:`-` Users will be able to see the address of the asset instead of the redundant asset name in the "Managed Assets" view and in the "Newly Detected Tokens" view.
* :feature:`7015` Users will be able to sort the blockchain accounts by displayed name.
* :feature:`7024` When a Uniswap-V2 or Sushiswap deposit gets decoded it will update the default symbol of the LP token to include information about the underlying tokens.
* :bug:`7017` Fix the issue where clicking on the chain in the blockchain balance summary didn't show the correct section.
* :bug:`6999` Chai token balances should not appear doubled under certain conditions.
* :bug:`-` Fix styling issue with the lock icon for "Add collateralization ratio watcher" for non-premium user.
* :bug:`-` Fix issue where the reports page cannot be loaded if there is old report from older version.
* :bug:`-` Fix the issue where the app freezes for a few seconds on logout.
* :bug:`7009` PnL reports with an old type of event (such as DailyStats) following a swap will no longer fail with an exception.
* :bug:`6998` If a username contains a '.' the user will now be able to log in properly again.
* :feature:`6885` Users can now specify EVM chains for which no activity will be auto-detected by rotki.
* :bug:`-` The welcome message at first login after a version upgrade will now have the correct link to the release notes.
* :bug:`-` Swaps using 1inch where the Uniswap V3 decoder processed part of the transaction will be correctly decoded now.
* :bug:`-` Creating, editing and deleting accounting rules will now update warnings when rendered events get affected in the history view.
* :bug:`-` Showing a page with a history event with a non-recognized type/subtype combination will no longer stop the page from loading due to an error.

* :release:`1.31.0 <2023-11-24>`
* :feature:`-` Oneinch v3 swaps should be supported in Ethereum mainnet.
* :feature:`-` Attestation events for the Ethereum Attestation service in Mainnet, Optimism, Arbitrum One and Base will be properly shown to the user.
* :feature:`-` Compound v3 reward claims should now be shown properly
* :bug:`-` Uniswap Swaps with the Universal router would be decoded correctly.
* :bug:`-` There will be no duplicated balances in cases where the native token balance is zero.
* :bug:`-` Fix the issue where users sometimes encounter timeout errors when importing assets from a zip archive.
* :bug:`6871` Ethereum staking withdrawals querying should now work fine again.
* :feature:`6439` Users can filter historical events to display only customized events.
* :bug:`6548` Users will no longer be blocked by a persistent modal dialog while premium sync is uploading.
* :bug:`-` Replaces snowtrace.io with avascan.info as the default explorer for Avalanche C-Chain
* :feature:`-` Users will be able to create custom rules for accounting.
* :bug:`-` Fix the issue where pinned PnL report errors (missing acquisitions and missing prices) become empty when the user moves to another page.
* :feature:`-` Migrating MATIC to POL in ethereum mainnet is now properly decoded.
* :feature:`-` Users can now see if any of their addresses have vCOW available to claim from the CoW Protocol airdrop.
* :feature:`-` Golem's GNT->GLM migration events will now be properly detected.
* :feature:`6688` Add support for Woo Centralized Exchange
* :feature:`-` Users will be able to modifying (add/edit/delete) all history events types.
* :feature:`-` Users will be able to customize the accounting rule for historical events.
* :feature:`-` Octant GLM locking/unlocking events will now be properly detected and shown to the user.
* :feature:`6733` Added support for detection of GRT tokens delegated to indexers in The Graph protocol (amounts including rewards).
* :feature:`-` Binance CSV importing will now recognize more entry types.
* :feature:`6712` The Graph protocol support has been added. The events related to delegator staking now will be properly displayed and accounted for.
* :feature:`5843` Velodrome is now supported in Optimism. Related transactions should be decoded properly and shown in human readable format and any balances in Velodrome auto-detected.
* :feature:`630` Users will be able to export history events to CSV.
* :feature:`6582` Users will be able to see skipped external events on the history events page, export them to CSV, and reprocess those events.
* :feature:`6621` Transactions involving the SDAI contract will now be properly decoded.
* :feature:`-` Base support has been added. Balances will be shown, transactions pulled and decoded and taken into account in the PnL report.
* :feature:`1591` Gnosis chain support has been added. Balances will be shown, transactions pulled and decoded and taken into account in the PnL report.
* :feature:`-` ENS and DIVA governance voting related transactions will now be properly decoded and shown to the user.
* :feature:`6275` Transaction events from bitstamp CSV can now be imported
* :feature:`-` Properly decode optimism bridge 2 step withdrawal proving transactions
* :feature:`2000` Users will now have the ability to filter between claimed and unclaimed airdrops.
* :feature:`-` Transactions bridging from/to Base using the official bridge will be now decoded.
* :bug:`-` History event header will now be visible only on mobile.
* :bug:`6647` When PnL report generation is finished, users will not be redirected to the report page, but will get notified instead.
* :bug:`6667` Wrong ENS name should no longer be reported for some edge case of ENS actions and the name should also appear in more events than before.
* :bug:`-` Aave v2 accounting for deposit interest profit and borrow payback loss should now work correctly again.
* :bug:`6717` Fixes an issue causing the graph for some multichain assets to not be displayed correctly.
* :bug:`6169` Handle some kraken event categories better and show them in the UI. Categories like failed withdrawals, moving funds from/to staking and credits of forked assets or delisted asset trades.
* :bug:`-` Users will be able to import custom assets from the assets backup file.
* :bug:`-` Fix issue for some users where the datepicker field is not automatically filled with current datetime
* :bug:`-` Fix issue with editing ledger entries whose rate is not set.

* :release:`1.30.2 <2023-09-21>`
* :feature:`-` Improved support for importing Binance CSV files.
* :bug:`6625` Error text when merging assets will now appear properly.
* :bug:`-` ENS registrations that involve a refund to the user due to paying too much should reflect the proper amount in the decoded event.
* :bug:`6597` Transactions involving ENS labelhashes with odd number of digits will now be decoded correctly and the entire decoding process should not halt if they are encountered.
* :bug:`-` Substrate balances in the blockchain & accounts view will now display correctly.
* :bug:`6587` All Kraken special & staking assets, like staking assets bonded for a specific time will now be handled properly.
* :bug:`-` Pointed to the new yearn finance API domain.
* :bug:`-` rotki will now prevent users from merging EVM tokens.
* :bug:`6550` Custom imported rotki events will now be taken properly into account in PnL and shown as recognized in history events view.

* :release:`1.30.1 <2023-08-23>`
* :bug:`-` Last premium DB upload will now show the last known DB upload time from the remote and not the time the local app did its last upload. This is important for people using multiple machines.
* :bug:`6528` Spam assets will be synced across accounts sharing the same globaldb and won't be queried during token detection.
* :bug:`-` Removed deprecated "Reset DB button" from the aave/yearn view.
* :bug:`6524` Premium users will be able to explicitly request to force push their local DB to the server backup properly again.
* :bug:`-` Fix an issue where certain gitcoin donations were not detected in optimism and where the big transfer to the contract which later splits into the donations was mistakenly kept.

* :release:`1.30.0 <2023-08-17>`
* :feature:`6444` Users will now be able to see the asset graph in asset collection view.
* :feature:`6274` Staking events from cointracking CSV can now be imported properly
* :feature:`6041` Add external service timeout settings.
* :feature:`6426` Users will now be able to import their BitMEX wallet history files.
* :feature:`-`  Gnosis safe transaction execution or failure is now properly shown in the decoded history events.
* :feature:`-`  The database size for users who have EVM transactions of any chain is now greatly reduced. Some databases had a reduction of up to 40%.
* :feature:`6033` Optimism gas calculation is now correctly taking into account L1 gas fees.
* :feature:`-` Optimism governance votes that include parameters should now be decoded properly.
* :feature:`-` Users will now be able to check their addresses able to claim the DIVA airdrop.
* :feature:`-` DIVA token airdrop claim and delegations are now properly shown in the decoded history events.
* :feature:`-` Transactions for adding, removing and changing owners threshold for a gnosis safe multisig will now be decoded properly.
* :bug:`-` Fix an issue where MEV rewards could not be correctly accounted and exported in the CSV summary.
* :bug:`-` ENS names that use the new RegistrarController and are renewed will have their events properly detected.
* :bug:`-` Fixed an error that prevented from exporting the PnL report with debug information.
* :bug:`-` Fixed an error affecting compound decoders where having more than one asset with the same symbol made the decoding fail.
* :bug:`-` Fix a bug where the ETH asset is not shown correctly in the location breakdown when the 'Treat ETH as ETH2' setting is activated.
* :bug:`-` Improve date and hexadecimal address scrambling.
* :bug:`-` Fix an error affecting the events pagination for non premium users.
* :feature:`3420` Arbitrum One support has been added. Balances will be shown, transactions pulled and decoded and taken into account in the PnL report.
* :feature:`6454` The balances snapshot csv file exported from rotki now contains an asset symbol column.
* :bug:`-` Remote errors should no longer affect the ethereum staking deposits decoded event view.
* :bug:`-` Newer deposits to zksync lite should be decoded properly in the history events view.
* :bug:`-` Using SVG icons for assets will now work.
* :bug:`5038` The rare error some premium users got: "Plaintext DB is locked" should no longer happen.
* :feature:`-` All gitcoin v2 related events are now properly decoded across supported EVM chains.


* :release:`1.29.1 <2023-07-27>`
* :bug:`-` Fix a bug where some images indicating the location of the assets are not loaded.
* :bug:`-` Errors creating a premium account with an invalid premium key in Windows are now handled gracefully
* :bug:`-` Doing multiple simultaneous filter asset searches no longer results in Global DB locked error.
* :bug:`-` Removing an evm address will no longer affect metadata such as detected tokens of the address if it is also tracked for another evm chain.
* :bug:`-` DSR balances that are held via a proxy contract will no longer appear duplicated under some specific circumstances.
* :bug:`-` Fix issue where users cannot add non EVM asset.
* :bug:`-` Fix bug on the `<date-time-picker />` component, where the validation for future dates was broken when selecting a different timezone. This also fixes the issue with the cursor, while the user is editing the number in the middle.
* :bug:`6350` Graceful handling of EVM rpc node returning non-int block number.
* :bug:`6349` Fix issue where users may see an assets update conflicts dialog that does not appear to have any size.
* :bug:`6358` Handle avalanche error at checking address activity gracefully.
* :feature:`-` Premium users will be able to backup larger DBs if they use the sync functionality.

* :release:`1.29.0 <2023-06-28>`
* :feature:`-` ENS name transfers will now be shown properly and not just as generic ERC721 transfers.
* :bug:`-` Fix issue create account always saving submit_usage_analytics as true.
* :feature:`2822` In the asset graph, users will see another setting `Infer zero timed balances` which when activated will show the periods when users weren't holding the asset.
* :feature:`-` Transactions changing the content hash of an ENS name will now be properly decoded.
* :feature:`5255` Pnl report assets now have an etherscan link to make it easier to identify pool assets.
* :feature:`6179` Users will now be able to import their trades, income and spending from BitcoinTaxes.
* :feature:`-` Ethereum transactions involing bribe claim payouts from StakeDAO will now be decoded properly.
* :feature:`-` Ethereum transactions involving locking and unlocking GNO using the locked GNO contract will now be decoded properly.
* :feature:`5250` Ethereum transactions involving AAVE v1 and v2 liquidations will now be decoded properly.
* :bug:`-` Fix issue for ledger actions with zero rate, where the rate isn't used in the PnL report.
* :bug:`-` Events where the user withdraws WETH from a Uniswap V2 liquidity position will be now correctly decoded.
* :bug:`-` ENS avatar fetching for each name's avatar should now work for all name resolvers. Even older or custom ones.
* :bug:`-` Users will be now able to add multiple EVM tokens with the same name if the address is different.
* :bug:`-` Users will now see correctly decoded Kyber legacy trades.
* :bug:`-` Users will now be able to decode compounding transactions for Convex gauges.
* :bug:`-` Events depositing tokens in Yearn V2 vaults where the full owned amount is deposited should be now correctly decoded.
* :bug:`-` Users will no longer see double counting of balances in curve gauges.
* :bug:`-` Aave transactions that deposit ETH in a contract that uses WETH will now be correctly decoded.
* :bug:`-` Events that were imported via a csv file will now be properly accounted for in PnL reports.
* :bug:`-` Notes in exported CSV reports will contain the correct url for transactions in different EVM chains.
* :feature:`-` The PnL report page will load faster if there is many old reports in the DB.
* :feature:`-` Convex staking and Curve gauge balances will no longer need a manual balances refresh to be detected.
* :feature:`-` Cowswap trades should now display the fee separately as a different event.
* :bug:`-` If the relay reports an mev reward with same recipient and amount as block reward, do not create a duplicate block mev reward.
* :bug:`-` Transactions containing anonymous events should now be properly decoded.
* :feature:`-` Events involving curve gauge voting should now be properly decoded.
* :feature:`-` 1inch v4 events should now be properly decoded.

* :release:`1.28.0 <2023-05-17>`
* :feature:`2469` History events have now been unified under a common history events section. At the moment it features all kraken exchange events, evm events, custom imported events, block productions, staking withdrawals. Missing events retain their own sections and will be merged into the unified history in subsequent releases.
* :feature:`3973` Users will now be able to track their profit in Liquity staking and stability pool.
* :feature:`5473` Block production rewards for your validators will now be properly detected, displayed and accounted for in the PnL report.
* :feature:`4886` Staking MEV rewards for your validators will now be properly detected, displayed and accounted for in the PnL report.
* :feature:`5933` FTX and FTX US support is removed since the exchanges no longer exist
* :feature:`5824` Improved support for ENS, allowing to decode the version of their contracts that added the name wrapper.
* :feature:`-` Refunds in ENS renewal transactions will now be properly processed.
* :feature:`5816` The NFT images will not be automatically rendered now. It is made so to prevent a known security issue, that may result in leakage of your privacy (read https://medium.com/@alxlpsc/critical-privacy-vulnerability-getting-exposed-by-metamask-693c63c2ce94 ). You can add domains you trust to the whitelisted domain in the NFT setting.
* :feature:`5696` Transactions interacting with Curve Zap Deposit contracts are now decoded properly.
* :feature:`5761` Liquity transactions that were made via DSProxies will now be properly decoded.
* :feature:`5798` Users will now be able to see ENS avatars for addresses.
* :feature:`5676` Curve gauge deposit, withdrawal and claim rewards actions will now be correctly decoded.
* :feature:`5677` Swaps made on Curve in ethereum mainnet will now be properly decoded as trades.
* :feature:`1505` Users will now be able to see breakdown of Binance/Binance US exchange balances, which are in account balances, and which are in savings/lending. The interest history also will be taken into account in the PnL report.
* :feature:`5639` Cowswap transactions are now decoded properly.
* :feature:`5582` Users will now be able to add their own tx hash, if somehow rotki failed to detects it.
* :feature:`5588` Users will now be able to save and restore used filters in the history section.
* :feature:`5587` Forward/Backward navigation for filters/pagination (using mouse buttons) will now be possible in the history section.
* :feature:`5569` It is now possible to detect when an evm address is used in other chains and start tracking it. Also a background task runs periodically that performs this check.
* :feature:`3004` Users will now be able to automatically track balances in convex gauges and their locked and staked CVX.
* :feature:`5611` Users will now see an improved notification if their API keys for Etherscan are missing and it will be easier to take action on it.
* :bug:`5491` Show original manual latest price asset in manual balance form.
* :bug:`5572` Fix a detection error that caused some uniswap v2 trade edge cases not to be accounted for properly in pnl report.
* :feature:`5592` Either include fees in the bought assets price or treat them as standalone events depending on the accounting settings.
* :feature:`-` For known protocols like yearn, curve, uniswap etc, if the on-chain price query fails, external oracles will still be queried in case something is found there.
* :bug:`5825` Eth staking view overview numbers will no longer be limited to the past year.
* :bug:`-` Yearn vault price queries will now work more robustly. If the underlying token is not in rotki's DB it will be queried from the chain.
* :bug:`-` Fixed a bug where balancer icon is not showed as transaction event counterparty.
* :bug:`5672` Exported csv files after using ACB as the cost basis calculation algorithm will now reflect the same numbers as shown in the app.
* :bug:`-` Fixed an issue importing events from BlockFi when the assets' symbol use lowercase instead of uppercase.
* :bug:`-` Ethereum transactions claiming COMP after comptroller's COMP ran out and has been refilled will now be decoded correctly as COMP rewards.
* :bug:`-` Fixed an edge case where removing an EVM account multiple times in a row, while a transactions querying task ran, would result in an error.
* :bug:`-` Ignoring forked assets ETC, BCH and BSV for accounting should now also remove any pre-fork references of them and completely omit them from the PnL report.
* :bug:`-` Users with kraken accounts with old data that were never purged and repulled will no longer have missing events.
* :bug:`-` Fixed a bug that didn't allow adding a new Bitpanda account.
* :bug:`-` Handled ETH2 staking rewards conversions in Kraken after the activation of withdrawals.
* :bug:`-` PnL report will now correctly show progress bar percentage if user has connected but non-syncing exchanges.
* :bug:`5697` Tokens returned to the user when decoding Balancer V1 deposits won't be detected as received wrapped tokens.
* :bug:`5749` Phishing zero token transfer transactions will now be hidden and ignored.
* :bug:`5717` Swaps will now be processed in accounting correctly even if set manually.
* :bug:`5847` Dev users: Querying the all balances api endpoint multiple times within 15 mins under certain conditions will no longer double some asset balances.
* :bug:`-` If a premium user changes their rotki password they will now be able to pull remote data without restarting the app.
* :bug:`-` Now there won't be errors querying balances when an address owning a Makerdao vault is deleted.
* :bug:`-` Fixed an issue where reports couldn't be exported if there was special characters in notes or assets and the user locale was not compatible.
* :bug:`-` When users edit exchange credentials, if new credentials are invalid, the old passphrase will now be kept.
* :bug:`5934` When an exchange account is deleted from rotki and there are still more tracked accounts on the same exchange, events will no longer be re-queried for those remaining accounts.
* :bug:`-` Users will now see the correct set of NFTs if they customized the list of addresses queried for the NFT module.
* :bug:`-` Withdrawals from curve pools with aave wrapped tokens will now be decoded correctly.

* :release:`1.27.1 <2023-02-24>`
* :feature:`-` Transactions involving Sai CDP migration to Dai CDP are now properly decoded.
* :bug:`-` Fixed a bug where token balance detection for EVM tokens with many addresses may not have worked properly.
* :bug:`-` Fixes bug where an error message is not shown when some input filled with incorrect value.
* :feature:`5576` Added support for WSTETH, RETH, GNO and other collateral type makerdao vaults. Also added code to autodetect new collateral type makerdao vaults in the future (so long as ABI stays the same).
* :bug:`-` Fixes bug where Maker Vault Collateralization Ratio can't be edited in watcher form.
* :bug:`-` Fixes bug where wrong account label was used in asset location breakdown.
* :bug:`5560` EVM transaction events should now be properly ignored in accounting.
* :bug:`-` Fixes bug where asset breakdown wasn't displayed correctly in the exchange balance section.
* :bug:`-` Fixes bug where navigation bar on the left didn't expand by default.
* :bug:`-` Fixes curve deposits and withdrawals accounting.
* :bug:`5561` Fixes average cost basis calculation.
* :bug:`-` Fixes bug when some decoded events in transactions would disappear.
* :bug:`-` Transactions that happened in genesis block are now properly decoded

* :release:`1.27.0 <2023-02-03>`
* :feature:`5015` EVM assets across multiple chains will now appear together in the dashboard, with an option to break them down into their per-chain holding.
* :feature:`-` Users will now be able to see newly detected token section under "Manage Assets" menu, so it will be easier to add any spam assets to the ignored tokens list.
* :feature:`4416` Transactions that have interacted with the single collateral DAI CDP contracts are now properly decoded.
* :feature:`5150` Add option to abbreviate large number. For example to show 1.234.567 as 1.23 M.
* :feature:`4940` Users will now be able to reset the assets database without losing any custom information they may have added.
* :feature:`4487` Users can now customize the order of how addresses are resolved to human readable names.
* :feature:`5001` The PnL report can now be generated with the Highest-In First Out (HIFO) accounting method.
* :feature:`1793` The PnL report can now be generated with the average cost basis accounting method.
* :feature:`5148` Users will now see tokens detected for accounts having a DSProxy.
* :feature:`5526` Users will now be able to read the name of the profit currency when moving the mouse over the currency symbol.
* :feature:`4912` Users can now ignore individual NFTs and they will not appear in the dashboard balances or snapshots.
* :feature:`5050` Users can now add a custom image/icon for each custom asset they own.
* :bug:`4332` Price oracles are now temporarily penalized after repeated failures.
* :bug:`5402` Fix issue where the wrong filepath is used when deleting user DB backup in Windows.
* :bug:`-` Fixed an edge case where users would be swamped with "This socket is already used by another greenlet" errors during websocket communication between backend and frontend.
* :bug:`-` Transfers of ether between tracked accounts will now have a correct label in the UI.
* :bug:`-` Trades involving delisted bitfinex pairs will now be properly read by rotki.
* :bug:`5390` Profit for ethereum validators will now be handled correctly if the deposit was made on beacon chain genesis.
* :feature:`784` Add support for OKX exchange
* :feature:`-` Swaps made via uniswap v3 auto routers (both v1 and v2) will now be decoded correctly.
* :feature:`3231` Optimism is now supported. Optimism balances will be shown and optimism transactions will be decoded.
* :feature:`1756` Uniswap and sushiswap pool join/exit events are now properly decoded and taken into account during PnL report.
* :feature:`5463` Deposits into the eth2 contract should now be decoded correctly
* :bug:`-` Fixed an issue where price for pairs of fiat currencies was not queried properly.
* :bug:`-` Customized ownership proportions of validators owned by eth1 addresses will now be properly respected.
* :bug:`-` If an exchange location is set as non-syncing but has also been removed, attempting to query for it will no longer query all exchanges.

* :release:`1.26.3 <2022-12-30>`
* :bug:`5315` Fix issue where balance is not fully refreshed after detect tokens button pressed.
* :bug:`-` Connecting to substrate nodes will no longer timeout prematurely for systems with slow connections.
* :bug:`-` Transfers between tracked accounts will now have a correct label in the UI.
* :bug:`-` Users will be able to finish balance queries if they have assets with missing information.
* :bug:`5265` Visiting the trades page will no longer query trades from ignored exchanges.
* :bug:`5038` Premium users with big databases should no longer see the error: "Upload data to server died with exception: database plaintext is locked".
* :bug:`-` Tokens added by the Balancer module will now have the name field correctly set.
* :bug:`-` If a user removes the API keys for an exchange, actions on that exchange will no longer be excluded from PnL reports.

* :release:`1.26.2 <2022-12-09>`
* :bug:`5187` Fix issue where the blockchain balances were refreshed, when only changing the label or the tags of an account.
* :bug:`5170` Fix issue where loopring balances is not updated when blockchain balances are manually refreshed.
* :bug:`-` Users will now be able to import binance trades of type Buy + Transaction Related from CSV exports.
* :bug:`5127` Uniswap V3 swap transactions are now decoded properly.
* :bug:`5124` Users will now correctly see all the events related to lending in the defi view.
* :bug:`5126` APR and APY for borrowing and lending in Aave should properly show again.
* :bug:`5128` Ethereum transactions where no value was transferred will now be correctly decoded.
* :bug:`-` Uniswap V3 oracle will now correctly skip assets with no liquidity when querying prices.
* :bug:`2934` Users will now be able to deploy the docker image on a subpath instead of the root domain.
* :bug:`-` Users won't get errors querying prices due the usage of defi oracles for querying prices of NFTs.
* :bug:`-` Fix an edge-case problem with synchronizing database with the server.
* :bug:`-` Users will be able to edit EVM tokens again and the information about underlying tokens will be correctly displayed.
* :bug:`-` Fix an issue with nginx websocket proxying on docker.
* :bug:`-` Now `Card Cashback Reversal` entries from cryptocom csv will be imported correctly.
* :bug:`-` Default list of open nodes has been modified. Users who used only defaults may notice an increase in speed. For others it depends on their selection and they are encouraged to review and modify their ethereum nodes list.

* :release:`1.26.1 <2022-11-04>`
* :feature:`5144` Add HIFO and ACB options for cost basis method.
* :feature:`5114` Add an option to reset the global DB assets that are known by the app to their original state. A so called soft-reset.
* :feature:`5102` Show stability pool to liquity module.
* :feature:`5080` For custom assets with custom price there should no longer be any double conversion. So 1 euro should always be one euro.
* :feature:`5046` Users who deleted important assets from their rotki instance will now have a fallback and won't get their rotki stuck.
* :bug:`5041` Add an option to only show ignored assets in assets table.
* :bug:`5052` Provide a fix for the edge case at 1.25.3->1.26.0 (v34->v35) DB upgrade that caused a FOREIGN key error and botched the upgrade.
* :bug:`-` Having SOL in custody of bitcoin.de will now work properly again.
* :bug:`5051` Windows users with a premium subscription should be able to upload their user DB for backup to our server properly again.
* :bug:`4821` Provide a fix for an infinite loop querying FTX trades if many trades were made in a short time.
* :bug:`5073` Rotki won't fail to start at an edge case of starting the app again after more than a year when a particular global DB table that is expected is missing.
* :bug:`-` Acquisitions in onchain swaps won't be taxable in PnL reports.

* :release:`1.26.0 <2022-10-28>`
* :feature:`2607` Users can now add general and section specific notes in rotki by clicking on the note icon on the top right menu.
* :feature:`4906` Add supports for custom assets.
* :feature:`4675` Added YFIETH-f curve pool to the list of known assets.
* :feature:`4676` Now curve pools are automatically detected in the background each week, and more pools are supported.
* :feature:`4755` Add mass delete functionality for trades and ledger actions.
* :bug:`4722` Show unsupported error when running rotki on Windows 7.
* :feature:`4449` Add Taproot (P2TR) option when adding Bitcoin xpub.
* :feature:`2770` Add generic CSV import functionality.
* :feature:`1830` Bitcoin and Bitcoin Cash addresses are now derived from XPUBs when balances are refreshed.
* :feature:`4602` Shows indicator that indicates whether ETH nodes are connected or not.
* :feature:`1744` LP balances (Uniswap V2 & V3, Sushiswap, Balancer) should now appear in the dashboard and be taken into account in the snapshots.
* :feature:`3249` Add Uniswap V3 LP Positions Functionality.
* :feature:`4600` User will now be notified if a leftover backend process is running when starting rotki.
* :feature:`1224` Windows binaries should now be signed and the warnings that the software is not trusted should slowly go away.
* :feature:`4704` Management of ignored assets is now moved to asset settings.
* :feature:`-` Ethereum transactions involving convex finance should now be automatically decoded.
* :feature:`1705` Ethereum token for each address will no longer be automatically detected with each query. Query speed performance improvement.
* :feature:`-` Transactions that have interaced with the WETH contract are now properly decoded.
* :feature:`-` An ethereum address's tokens can now be manually detected by pressing a specific button in the UI.
* :feature:`-` Transactions involving uniswap v2 and uniswap v3 will now be properly decoded in the ethereum transactions view
* :feature:`2701` Multi-evm assets are now supported. All EVM assets display the chain they correspond to in the UI.
* :feature:`2270` Users can now import generic data into rotki via a rotki CSV import option.
* :bug:`-` When force sync fails a proper error message is displayed
* :bug:`-` If something is wrong with an asset update, it won't end up having partial information.
* :bug:`4930` Taxable ledger actions that spend fiat currencies should now be properly seen as taxable.
* :bug:`4870` ETH2 staking view should no longer freeze for too many validators.
* :bug:`-` Decimals now defaults to 18 when token contract info query fails.

* :release:`1.25.3 <2022-09-02>`
* :bug:`4781` Failure in one specific binance endpoint during balance query won't fail the entire binance balances query unless it's the main spot balances endpoint.
* :bug:`4769` Fixed various issues with adding/editing/deleting web3 nodes. Editing the name of a node now works and also setting all open nodes to 0% query probability should no longer throw a 500 error.
* :bug:`4710` Users will again be able to import CSV from certain importers.
* :bug:`-` Bisq importer will now use the correct amount in all the imported trades.
* :bug:`-` Addition of same addresses and xpubs on Bitcoin and Bitcoin Cash now should work properly and balances should be correct.

* :release:`1.25.2 <2022-08-17>`
* :feature:`-` The add button in blockchain accounts & balances is now bigger on larger screens.
* :bug:`4671` Fixes an issue with the auto-updater not working properly.
* :bug:`4657` Now ens names are verified by forward resolution.
* :feature:`4645` Support the new poloniex API. Note that with their "new and advanced" API we can't query trades history older than 1 week.
* :bug:`4682` Premium users will again be able to load the dex trades section correctly.

* :release:`1.25.1 <2022-07-28>`
* :bug:`-` Introduce an experimental approach to ignore uniswap v2 pool pricing for pools with single sided liquidity that is less than $5k. This is experimental and we will probably figure out a better way to filter spam assets in the future. Context: https://twitter.com/peter_szilagyi/status/1552532767790997504
* :bug:`4599` Users will see a smaller amount of icons when accessing rotki from a mobile device.
* :bug:`4578` Value distribution by asset now respects ETH=ETH2 setting.
* :bug:`-` Some cases of python segfaulting under specific conditions of reading/writing to the DB should now be fixed.
* :bug:`4586` DB yielding instructions is now an argument and can be configured by the user. It can be set to any positive integer or zero to disable it. There is a class of bugs that can lead to crash of the backend when this is enabled, so disabling is now an easy way to avoid them. With this enabled DB access parallelization is achieved for long running queries.
* :bug:`4606` Fixes missing decimals when editing a manual balance while having custom decimal and thousand separators.
* :bug:`4597` Tokens with no information about decimals won't make the price query stop if the uniswap oracles are used.
* :bug:`4502` Nexo importer now supports updated format.

* :release:`1.25.0 <2022-07-15>`
* :feature:`3325` Users will now be able to manage all ethereum nodes queried, their querying priority and add any arbitrary number of nodes to query.
* :bug:`4438` Filtering of ethereum transactions is now enabled.
* :feature:`2219` Users will now be able to edit balance snapshots.
* :feature:`4495` Users will now be able to toggle ETH staking taxation.
* :feature:`1420` Add address book for ETH addresses.
* :feature:`-` Add zoom feature for line charts.
* :feature:`3095` The application will now notify the user if there is a status change for the premium subscription.
* :feature:`1028` Native support for Bitcoin Cash blockchain.
* :feature:`4268` Add a premium setting to follow the system's theme.
* :feature:`4243` Users will now be able to refresh the icons of an asset
* :feature:`3798` Users will be now able to combine ETH and ETH2 and display it as one in the interface.
* :feature:`4099` Users are now able to export an event list of a PnL run to provide to the developers for debugging purposes.
* :feature:`44` Add option to change cost basis method (FIFO and LIFO order).
* :feature:`4067` macOS compatibility has been improved with native support for Apple Silicon. Now two binaries for x86 and ARM architectures are generated.
* :bug:`-` Now no missing acquisitions should appear for fiat assets during accounting.
* :bug:`4459` Transactions that happened in genesis block are now queried and stored properly.
* :bug:`4530` Movements from Bitstamp should now be correctly read if the asset is known.
* :bug:`-` The electron application will now terminate properly if the backend fails to start.
* :bug:`-` Now querying ens names for an empty list of addresses won't be causing an error.
* :bug:`4456` Now NFTs query should not raise any unhandled error during the process of adding new ethereum addresses.
* :bug:`-` Fix empty asset location distribution for ETH2.
* :bug:`-` In a rare edge case the database with past profit and loss reports won't block the version upgrade process.
* :bug:`4417` Activating privacy mode will now also scramble the value, to prevent other users from estimating the value (e.g. By estimating the length of digit of the value, or using advanced software to unblur the text).
* :bug:`-` ERC20 approves for tokens that do not have the event arguments indexed such as finance.vote will now not break rotki.
* :bug:`-` Asset value distribution graph will no longer include ignored assets.

* :release:`1.24.1 <2022-06-03>`
* :bug:`4383` Removing an address while running a PnL report should now work.
* :bug:`4379` For many ethereum transactions the entire app should no longer hang. This is a temporary fix until a proper one is implemented. With this fix we temporarily remove the ability to filter in the ethereum transactions view.
* :bug:`4425` Makes periodic premium checking task less strict. Also introduces automatic reactivation.
* :bug:`4398` Fix asset type selection that cannot be enabled for new asset addition.
* :feature:`4401` The options for remember username and password are now separated.
* :bug:`4386` Blockfi import for transactions now supports 'Crypto Transfer'
* :bug:`4420` Transactions with the old WETH contract and other contracts that don't have decimals, symbol and name should now be decoded properly.
* :bug:`4378` Ask for users permission to access keychain only when `Remember Me` option at login screen is enabled.
* :bug:`4384` Price caches filter should now be working again.
* :bug:`-` Acquisitions for which no price can be found will still appear and not count as missing acquisitions.
* :bug:`4122` Kucoin users should be able to retrieve information for old trades again.
* :bug:`-` COMP price before 20/06/2020 will not be hardcoded to $239.13 if queried via cryptocompare.
* :bug:`-` Prevent error while importing CSVs from cointracking when one trade row had a 0 amount bought.
* :bug:`4381` Fixes a problem at the DB upgrade between v1.23.4 and 1.24.0 which affected a subset of some kraken users.
* :bug:`4422` Account balances in blockchain accounts that contain ignored assets will now show the correct sum total net value.

* :release:`1.24.0 <2022-05-27>`
* :feature:`2221` All missing yearn v1 vaults should now have their balances detected and their historical accounting taken into account.
* :feature:`1797` All missing acquisitions and missing prices found during a PnL period are now gathered and shown to the user as actionable items at the end of the report generation.
* :feature:`4154` Binance data (trades, deposits, staking, etc.) can now be imported via csv file.
* :feature:`1115` Apply ENS reverse resolution to all Ethereum addresses shown in the frontend and if any have an ENS name associated with them, display that instead of raw address.
* :feature:`2890` Transactions in the PnL report are now clickable and have a link to the chosen blockchain explorer via the transaction hash.
* :feature:`1680` Users will now be able to see their 1inch v1 and v2 trades.
* :feature:`718` Users can now ignore an exchange from the PnL report using the same option as the one for exchange syncing.
* :feature:`2219` Users will now be able to delete balance snapshots.
* :feature:`4219` Users will now be able to import a balance snapshot manually.
* :bug:`4261` Fixes a problem were the docker container image size would increase on every restart.
* :feature:`1219` Introduces basic global search (you can go to any page in the app, do some basic actions such as adding a new trade or a ledger action, and also see prices of owned asset).
* :feature:`4249` Allow users to ignore asset from the asset overview page.
* :feature:`1106` Balance snapshots will now be created automatically without the need to restart the application or force a save.
* :feature:`2853` Add option to disable sync for connected exchanges.
* :feature:`3894` Users will now be able to download a balance snapshot by clicking a point at dashboard graph.
* :bug:`4172` Disallow addition and editing of external trade that could result in invalid trade fees.
* :bug:`4060` Treat reimbursement as a ledger action for crypto.com imports.
* :feature:`3370` Manual balance labels are now editable even after their creation.
* :feature:`4125` Introduces auto login mechanism for electron app.
* :feature:`1477` Adds classification for ETH transactions and their events.
* :bug:`4078` Adjust scrollbar color in dark mode for better visibility.
* :feature:`4071` Add option to reduce the animations effect.
* :feature:`3669` Users can export and import their custom assets.
* :feature:`4068` Introduces location overview page.
* :feature:`-` rotki no longer uses the gitcoin api or gitcoin CSVs to import information from gitcoin.
* :feature:`4030` Add copy functionality for amount display.
* :feature:`3987` Users will now be able to delete multiple database backups.
* :feature:`2934` Users will now be able to deploy the docker image under a sub directory behind a proxy.
* :feature:`569` Users will now be able to see assets staked, and amounts gained on Kraken's staking feature.
* :feature:`3838` Support for FTX.US has been added.
* :feature:`2216` Users will now be able to use Uniswap V2 and Uniswap V3 as price oracles.

* :release:`1.23.4 <2022-03-23>`
* :bug:`4072` Prevent users from inputting future date on trade and ledger action form.
* :bug:`4077` stkAave balance should no longer be double counted. Also unclaimed stkAave will appear in the balance (as Aave).
* :bug:`4059` Nexo importer won't consider `LockingTermDeposit` as another deposit.
* :bug:`-` BlockFi import for trades will use the correct rate.
* :bug:`3661` NFT won't be displayed as option while adding custom assets since the logic there is not compatible with NFTs.
* :bug:`4142` If an owned NFT has no image URL, NFTs will still be properly queried and shown in the frontend.

* :release:`1.23.3 <2022-02-04>`
* :bug:`4034` If a new premium user is created, with DB sync on, premium api keys being correct but wrong password is given then creating same user with right password will now work.
* :bug:`4013` Fix Bitpanda icon missing in exchange selector.
* :bug:`3983` Add loading indicator to data directory field.
* :bug:`4039` Rewards and cashbacks from crypto.com will now be correctly categorized as ledger actions.
* :bug:`3993` Fix app bar icons misbehavior when windows is resized.
* :bug:`3998` FTX subaccounts should now be working again.
* :bug:`-` If binance returns a delisted market as active and rotki queries it, the entire binance trade history query will not fail.
* :bug:`4010` Crypto.com users won't see errors for rows containing zeros.
* :bug:`-` All Liquity events will now always be correctly queried.
* :bug:`3947` Coinbase conversions will now choose in a better way the asset to nominate the fees.
* :feature:`-` Support for LUNA and card top ups has been added to the crypto.com importer.

* :release:`1.23.2 <2022-01-21>`
* :bug:`-` Users will now be properly prompted to restart the application after the auto-updater downloads the update.
* :bug:`3943` Users will now be able to properly add multiple accounts on Avalance even if they exist on Ethereum.
* :bug:`3964` Liquity Troves managed by a DSProxy will now see their events properly listed.
* :bug:`-` The application will now notify the user and exit if multiple backend binaries exist due to a failed update.
* :bug:`-` Kraken's KFEE will use the price of 0.01 USD when it is needed.
* :bug:`-` If a PnL report is ran for a specific period and there is more events after the period a warning for missing events and prompt to upgrade to premium won't show mistakenly anymore.
* :bug:`-` Query for AVAX balances will be more reliable now.
* :feature:`-` Users can now add an OpenSea API key to the external api keys page. Also some changes were made to try and improve opensea retrievals even without the user needing to input a key.
* :feature:`3952` Maker's WBTC-B, WBTC-C and MATIC-A vaults are now supported.

* :release:`1.23.1 <2022-01-14>`
* :bug:`3929` Prevent users from using invalid character for thousands and decimal separator.
* :bug:`3913` NFT Balances table at dashboard should be updated when users remove an ethereum account.
* :bug:`3916` Users with ethereum transactions that deploy contracts will now be able to load the transactions view properly.
* :bug:`-` Fix coinbase/pro detection for GTC, TRU and FARM.
* :bug:`3896` Fix dashboard balance search that does not show ethereum tokens.
* :bug:`3895` Popup for successful forced sync operation should show correct icon.
* :bug:`3899` Crypto.com users will now be able to import supercharger events and recurring buy orders. Viban purchases will also now be correct categorized.
* :bug:`-` Restores arm64 docker images.
* :bug:`-` AVAX balances should now be always correctly queried.
* :bug:`-` PnL report will correctly detect asset cost basis when the fee of a trade is nominated in the received asset.
* :bug:`3903` The application should now run on macOS 10.14 (Mojave) without errors.
* :bug:`3901` Coinbase accounts with internal subaccount movements will now display the Coinbase withdrawals properly.

* :release:`1.23.0 <2021-12-31>`
* :feature:`3324` Users will be able to set the percentage of ownership for jointly held eth2 validators.
* :feature:`3425` Users will be able to enter multiple pairs at once for binance exchange settings.
* :bug:`3847` Remove whitespace when inputting address in new asset form.
* :feature:`3842` Users will now be taken directly to create account when downloading the application for the first time.
* :feature:`-` Any ethereum transactions that were ignored for accounting will now need to be re-ignored.
* :feature:`1242` Users will be asked first whether to activate premium feature, and enable database sync when create new account.
* :feature:`2876` The application users will now be able to start the auto update mechanism manually from the update indicator.
* :feature:`2386` Users will see a separate section of L2 balances in Blockchain Balances section.
* :feature:`2382` Users will now be able to filter specific accounts such as the ones from Loopring using an automatically added tag.
* :feature:`2901` Users will now be able to select between a full privacy mode and a semi-privacy mode that keeps the percentages visible.
* :feature:`2624` Users will now be able to filter by tag in the asset details page.
* :feature:`2265` Users will now be able to see a hint for the trade rate when adding an external trade.
* :feature:`2848` Users will now get taken to the top of the table automatically when changing a page.
* :feature:`2121` Users can now select a different timezone when selecting a date to input.
* :feature:`1875` Users can now enable or disable specific time frames in the graph timeframe
* :feature:`2446` Users can now switch between adding an external trade using quote asset amount or trade rate.
* :feature:`2297` The application will now perform an update check every 24h (user-configurable) while the application is running.
* :feature:`3470` Users can now customize the date input format.
* :feature:`2918` Users can now select how the percentage column is calculated in the dashboard. Either based on total net value or based on current group (assets, liabilities, or nft).
* :feature:`3753` Application users will now be able to (copy, cut and paste) using the context menu .
* :feature:`3525` Users can now see the NFT icon at the NFT Balance table, and Non Fungible Balance table.
* :feature:`3176` Amount inputs will now adhere to the user specified amount formatting.
* :feature:`1214` Users will now be able to load and manage previously generated profit and loss reports.
* :feature:`3716` Users can now see if any of their addresses have PSP available to claim from the PSP airdrop.
* :feature:`824` Users will now be able to import their trade history from bisq.
* :feature:`1864` Users will now be able to see trades, deposits and withdrawals imported in CSV from exchanges not connected using API keys.
* :feature:`3685` Users will now be able to correctly read more transaction types in CSV files imported from crypto.com.
* :feature:`3497` Users will now be able to add ETH2 validators via index or public key.
* :feature:`3725` Users can now see if any of their addresses have SDL available to claim from the SDL airdrop.
* :feature:`3708` Users will now be able to see trades from kraken made from their phone APP and in the kraken's swap UI.
* :feature:`3549` Users will now be able to select whether to include or not NFT total value in total net worth and graphs.
* :feature:`3712` Users will now be able to choose a custom date format while importing CSV files.
* :bug:`3767` The module selector will now properly clear after selecting a module by clicking.
* :bug:`3128` Bigger net worth values on dashboard should not overlap with the net worth graph.
* :bug:`3641` Users should now be able to view profit and loss reports that have many thousands of events without the UI freezing.
* :bug:`-` Deposits and withdrawals in files from cointracking will now be correctly registered.
* :bug:`-` ShapeShift CSV includes minerFee in rate, but outputAmount does not include minerFee.  Fix to account for the true transacted base amount.
* :bug:`-` Bitfinex users that used Spankchain in the exchange will now be able to see it properly in their trades, deposits/withdrawals and balances.
* :bug:`-` Users connected to Alchemy as a node will be able to properly retrieve old ethereum transactions.
* :bug:`-` Users whose only interaction with a yearn vault was a deposit will no longer see the entire deposit as loss in the PnL.
* :bug:`3804` Bitpanda users should now be able to see their crypto deposits and withdrawals.
* :bug:`3847` Inputting an address in the asset form with extra whitespace will now work properly thanks to trimming.
* :bug:`3859` Trades imported from crypto.com CSV should now have the correct rate imported.

* :release:`1.22.2 <2021-11-30>`
* :feature:`-` rotki will now detect locked SRM balances in FTX.
* :bug:`-` Kraken margin trades are not yet supported, so they won't show up or be taken into account in kraken trade history.
* :bug:`3744` Freshly created users who don't open the app again before an upgrade will now be able to update to new DB versions again.
* :bug:`3749` Users using multiple instances of the same exchange should now correctly see all their trades.
* :bug:`-` Liquity users won't make extra balances queries when using DSProxies.
* :bug:`3767` At module selection clicking on the module chip won't keep the text in the selection field.
* :bug:`-` Users will now be able to edit exchanges names for Kucoin and Coinbase Pro.

* :release:`1.22.1 <2021-11-19>`
* :bug:`3726` Manual liabilities should not count as assets and should be deducted from total net value when taking a snapshot. Also multiple liabilities of same asset should now be properly summed.
* :bug:`3722` Trades details will now properly expand one at a time.
* :bug:`3714` Airdrops section will now work again for Windows users.
* :bug:`-` Uniswap trades will be queried correctly now.
* :bug:`3724` Users should see their per asset liabilities properly aggregated on dashboard.
* :bug:`3702` RMRK for Kucoin and BCH for Bitfinex should now be properly recognized by rotki again.

* :release:`1.22.0 <2021-11-12>`
* :feature:`1146` Bitpanda exchange is now supported. Bitpanda balances are now shown and rotki can query trades and deposit/withdrawals from the exchange.
* :feature:`2483` Users will now get properly notified when saving the balance snapshot fails.
* :feature:`3579` Users will now be able to sort the NFTs in the gallery by name, collection and price.
* :feature:`3640` Liquity users that created troves using DefiSaver will be now able to track them.
* :feature:`1451` Improves performance of the Transactions page.
* :feature:`3594` Users can now sort the dashboard assets and blockchain balance per asset tables using the price field.
* :bug:`3328` The asset update resolution dialog should now be usable on mobile screens.
* :feature:`1513` Users will now be able to add manual liabilities.
* :feature:`1536` The Account & Balances add button will now be fixed to the right bottom of the screen. The blockchain balances add button will now properly select the appropriate blockchain based on the visible table.
* :feature:`3686` Users can now see if any of their addresses have ENS available to claim from the ENS airdrop.
* :feature:`3335` Users will now be able to find the pending tasks in the notification sidebar.
* :feature:`3235` Users will now be able to create and manage database backups, and view information related to the rotki databases.
* :bug:`3676` NFT collection floor price should now be properly retrieved again and shown as the valuation for user NFTs that have had no previous sales.
* :bug:`3667` Users should be able to upload asset icons to docker instances when using a remote connection via the application.
* :bug:`3664` Binance US users will no longer see errors regarding the fiat payments and orders endpoints.
* :bug:`3666` An ethereum token's address will be properly filled when navigating to the asset edit from the asset overview page.
* :bug:`-` Transaction receipts will now be processed properly even for nodes(such as open ethereum) that do not return the type field for non EIP1559 transactions.

* :release:`1.21.3 <2021-10-28>`
* :bug:`2178` Premium DB sync popup should no longer popup if you only use one instance of rotki in one system.
* :bug:`3643` The price currency will now be properly visible on the NFT balance header sorting when using a mobile device.
* :bug:`3629` Kraken api rate limiting should no longer cause a query to get stuck in a loop.
* :bug:`3624` Editing a CEX api key should now work properly again.
* :bug:`3619` Binance users should now be able to properly process fiat payments, deposits and withdrawals.
* :bug:`3613` Users should be now able to save a ledger action without specifying seconds.
* :bug:`3630` Users will be able to properly see their MakerDAO vault loans
* :bug:`3647` It should be now possible for users to properly ignore DEX trades in the trade history page.

* :release:`1.21.2 <2021-10-14>`
* :bug:`-` Users can now ignore any errors when force saving balances.
* :bug:`3576` User asset charts should no longer have arbitrary zero amounts. There is now a setting they can choose which is off by default. If set it denotes the multiplier of the snapshot saving frequency at which to insert 0 save balances for a graph between two saved values.
* :bug:`3578` Adding an external trade on a specific date without specifying time will now be possible. Any backend validation errors on the date field should now be properly visible.
* :bug:`-` The NFT gallery will correctly display NFTs that include a video extension but not at the end of the url.
* :bug:`3593` Sorting by asset in the dashboard asset table and blockchain balances per asset table should now properly sort alphabetically by the asset symbol.
* :bug:`3591` Uphold trades will reflect exchanged value instead of received value for base amount.  This will properly arrive at the received amount when the fee is accounted for.
* :bug:`3580` NFT balances will now get removed from the UI when the user deactivates the module.
* :bug:`3602` Kusama/Polkadot balances should now be queried properly again.
* :bug:`3603` The PnL execution will now continue despite potential error calling the compound subgraph.

* :release:`1.21.1 <2021-10-07>`
* :feature:`3554` Gemini users will now have their earn balances tracked in rotki.
* :bug:`3555` Users should now be able to see the total value in the table of NFTs in the dashboard
* :bug:`3579` Asset type selector will now be properly disabled when editing an asset.
* :bug:`-` Statistics per asset graph will now properly display the name of the NFT.
* :bug:`3547` Coinbase transactions without network data returned should now be processed properly.
* :bug:`3546` Coinbase users with trades/deposits/withdrawals/balances of FET (Fetch.ai) should have it properly detected.
* :bug:`2613` Graphs of assets that used to miss all 0 balance data points between two time point will now properly show a 0 amount in the asset graph for the time period.
* :bug:`3552` Users with semi-fungible tokens in different ethereum wallets will see them correctly in the NFT gallery.
* :bug:`-` Docker users will be able to retrieve automatic information for tokens when adding new ethereum assets.
* :bug:`3414` Coinbase conversions should display the correct fee.
* :bug:`3208` Rotki will now allow to track the same account for different blockchain types.
* :bug:`-` The value of NFTs will now be properly included as part of the total net worth when calculating an asset's percentage.

* :release:`1.21.0 <2021-09-30>`
* :feature:`3251` Users will now be able to easily access the asset edit page from the asset details page.
* :feature:`3020` Users will now be able to copy their ETH1 addresses when visiting the ETH2 staking page.
* :feature:`2362` Binance users will now be able to query their fiat deposit/withdrawals and fiat orders and have it taken into account in rotki.
* :feature:`3326` Introduces pagination for liquidity pool balances to help users with a great number of lps.
* :feature:`1097` Users will now be able to view their NFTs, track and manage their prices, and also see their value as part of their total net worth.
* :feature:`2764` Users will now be able to restore the local assets database to its initial state.
* :feature:`2847` Users will now be able to use a combination of filters in the search for trades and deposits/withdrawals.
* :feature:`3254` Users can now add a custom Covalent API key in rotki.
* :feature:`3416` Users will now be able to import ShapeShift trade history CSVs exported from shapeshift.com.
* :feature:`1345` Users will now be able to import uphold transaction history CSVs exported from uphold.com.
* :feature:`-` Users will now be able to track balances locked in pickle's DILL.
* :feature:`2891` Users will now see notes and links for trades in the exported CSV files.
* :feature:`2836` Users will now be able to track Liquity's troves and staking in the Liquity protocol.
* :feature:`3474` Users of coinbase will now see deposits for coinbase earn and inflation rewards.
* :bug:`3239` Users will now see only the relevant addresses suggested when filtering DeFi deposits.
* :bug:`3340` Users will now be able to properly see the favicon when accessing the frontend using Firefox.
* :bug:`3266` Users will now be able to properly access most of the top bar content using a mobile device.
* :bug:`3268` Users will now be able to properly scroll to the hidden tabs when using a mobile device.
* :bug:`3267` Frontend will now occupy all the available screen when accessed from a mobile device.
* :bug:`3463` Users using Turkish localization will now be able to use the application.
* :bug:`3448` Improve Kucoin api rate limit handling. Recognize CFG asset in Kucoin as WCFG.
* :bug:`3452` Trades from externally imported exchanges (blockfi, crypto.com etc.) should now be properly taken into accounting in the PnL report again.
* :bug:`3437` Fix a bug where for some active aave v2 lending positions the entire aToken balance would be shown as profit.
* :bug:`3406` Sushiswap events will now be taken into account during the profit and loss report.
* :bug:`3407` Users will now see correctly reported their amount of xSUSHI.
* :bug:`3421` Users will now be able to see solana properly in coinbase assets
* :bug:`3418` Users will now be able to finish import from crypto.com's CSV files when there is a time mismatch between rows.
* :bug:`3056` Users will now be better notified when an error occurred while importing information from crypto.com on credit/debit events with special cases.
* :bug:`3493` Users of Bitstamp will see correctly imported assets movements with fees in any coin.
* :bug:`3491` Coinbasepro users who own Barnbridge governance token (BOND) will now be able to properly see it in balances, trades and deposits/withdrawals.
* :bug:`-` Users importing information from Nexo CSVs will correctly detect interest gains and detect special assets symbols.
* :bug:`3502` MakerDAO vault users who saw double the amount of liabilities for some of their vault/s should now see the proper amount again.
* :bug:`3490` If a user had historic trades of a delisted asset in coinbasepro the trades query will now work again.
* :bug:`3535` There should no longer be a problem when changing active modules while an ETH account is already being added.

* :release:`1.20.1 <2021-08-27>`
* :feature:`3349` AMM swaps now have a transaction hash link in the trade history section.
* :bug:`3329` Users will now properly see their sushiswap trades in the history page if they have the sushiswap module activated.
* :bug:`3310` For the edge case of a MakerDAO vault event containing a zero amount the MakerDAO DeFi section and PnL report should no longer get an error.
* :bug:`3311` The PnL CSV export in Windows should now now longer contain the double number of lines and as such the formulas at the summary should be correct.
* :bug:`3313` Discrepancies on the sign of net_profit_loss in PnL CSV export between exports with and without formulas should now be fixed.
* :bug:`3355` Yearn V2 vaults should now display a correct price.
* :bug:`3373` The form to add a FTX account will now work correctly when the subaccount field is modified and then cleared.

* :release:`1.20.0 <2021-08-06>`
* :feature:`2426` Sushiswap is now supported. Premium users can see their LP balances, swaps history and LP pool join/exits. Finally the balancer trades are now taken into account in the profit/loss report.
* :feature:`2145` Users will now be able to customize whether CSV export should contain metadata of the PnL run. Consisting of the rotki version that generated it and the chosen accounting settings.
* :feature:`3279` Users will now be able to customize whether CSV export should contain a summary of PnL per event type.
* :feature:`3252` Users will now be able to customize whether CSV export should contain formulas or not.
* :feature:`3125` Native support for Polkadot blockchain.
* :feature:`3242` Native support for Avalanche Blockchain and Covalent API.
* :feature:`3097` Users will now have the option to disable the application tray icon.
* :feature:`3061` When inserting ledger actions users will now be able to skip the specific time on date input (00:00:00 will be assumed).
* :feature:`3061` Users will now get the last used location pre-selected when adding ledger actions.
* :feature:`3138` Users will now see separate cards on the Defi overview for MakerDAO Vaults and MakerDAO DSR.
* :feature:`3275` Users can now see if any of their addresses have FOX available to claim from the ShapeShift airdrop.
* :bug:`3264` Users should now be able to properly download the PnL CSV when using docker.
* :bug:`3289` Aave v2 balances should now be taken into account in the DeFi deposits section.
* :bug:`3287` Users with AMM trades from different AMMs in a single transaction will now be able to select all and deselect all trades properly in the frontend.

* :release:`1.19.1 <2021-07-22>`
* :bug:`3236` Users will now see the proper total networth for the current day in the graph tooltip.
* :bug:`3224` Users will now be able to properly select an end time in earlier dates.
* :bug:`3198` Firefox docker users will now see a regularly sized Gitcoin icon under the history menu.
* :bug:`3199` Users will now properly see the node connection status/last sync information update.
* :bug:`3214` UNIUP and UNIDOWN will now be correctly detected.

* :release:`1.19.0 <2021-07-15>`
* :feature:`3116` Support for INR (Indian Rupee) as a profit currency has been added.
* :feature:`1520` Users can now manually add prices for tokens/assets.
* :feature:`692` Gitcoin Grant owners will now be able to track and generate reports of their grants.
* :feature:`1666` Users will now be able to see their yearn v2 vaults in in the defi section.
* :feature:`2456` Users will now be able to correctly retrieve prices for Curve LP tokens.
* :feature:`2778` Users will now be able to enable modules and queried addresses when adding an ethereum account
* :feature:`1857` Premium users will now be able to query Aave V2 events.
* :feature:`2722` The sync conflict dialog dates will now be consistent with the user specified date format.
* :feature:`3114` Users can easily check and manage which addresses are queried for each defi module directly from the respective module page.
* :feature:`3069` When adding an asset coingecko/cryptocompare identifiers will now be validated and non-existing ones will be rejected.
* :bug:`3145` Docker users will now have the ability to logout any other sessions when attempting to connect from a new browser window.
* :bug:`2685` Invoking `--version` from the rotki backend binary in Windows should no longer raise a Permission error.
* :bug:`3142` During v26->v27 upgrade if a user has balancer LP events the upgrade should no longer fail.
* :bug:`3172` COIN should now be properly mapped to Coinbase tokenized stock in both bittrex and FTX.
* :bug:`3134` The new cWBTC token should now be properly recognized for compound users.

* :release:`1.18.1 <2021-06-30>`
* :bug:`2447` When fee of a trade is paid in crypto that crypto's asset will now be deducted from the cost basis calculation.
* :bug:`3133` Users will now properly see a MakerDAO entry in the Defi Overview.
* :bug:`2887` Upgrade the deprecated binance exchangeInfo and deposit/withdrawal APIs.
* :bug:`3118` Users will now be able to properly connect to the dockerized backend through the app. (It will not work if the docker container is a previous release).
* :bug:`3101` Editing ethereum token details via the asset manager in the frontend should now work properly again.
* :bug:`3100` FTX API keys with permission for subaccounts only will now be correctly validated.
* :bug:`3096` The Uniswap module will ignore swaps not made by the queried address.

* :release:`1.18.0 <2021-06-18>`
* :feature:`2064` Users will now be able to close rotki to tray. When logged the tray icon will update based on the net worth value during the selected period (week, two weeks etc).
* :feature:`2939` Rotki logs will now persist after restart. Number of logs and maximum size for all logs of a run can be now specified.
* :feature:`1800` Users will now be greeted with an informational notice when trying to access a page that requires a module to be activated.
* :feature:`1692` IndependentReserve users will now be able to see their balances and have their deposit/withdrawal/trade history taken into account during profit/loss calculation.
* :feature:`3025` Users will now see the percentage of each location when looking into an asset's details.
* :feature:`2596` Users will now be able to create new tags directly from the tag selection input.
* :feature:`2954` On login screen, the password field will now be focused for users that have remember user enabled.
* :feature:`2786` FTX users will be able to query information for subaccounts only.
* :feature:`2670` Users will now get results in a better order when using the asset selector.
* :feature:`2951` Users will now get results in a better order when searching for an asset in asset management. Search will now consider both name and symbol.
* :feature:`3014` Users will now get a suggested name when adding a new exchange.
* :feature:`1073` Binance users will now be able to select which markets should be queried for trades history considerably improving the speed of binance history queries.
* :feature:`3058` Docker users will now get notified when running an outdated version of the frontend cached in their browser.
* :bug:`3057` Nexo CSV importer will now use the correct time format.

* :release:`1.17.2 <2021-06-04>`
* :bug:`3043` Collapsed xpubs should now be included in the totals in the btc accounts table.
* :bug:`3029` Exchanges balances tab will properly adjust to a dark background on dark mode.
* :bug:`3027` Day should now display properly under all circumstances when a custom date format is evaluated.
* :bug:`81` Users with more than 10,000 trades in poloniex will now be able to properly pull their trading history.
* :bug:`3037` Querying a big number of legacy bitcoin addresses from an xpub should now work properly again.
* :bug:`3038` Binance.us queries should now work properly again.
* :bug:`3033` Users of Bitstamp should be able to pull their trades, deposits and withdrawals history again.
* :bug:`3030` Setting up a bitfinex api key should now work properly again.
* :bug:`3010` Fixes a bug when editing a trade that had a modified/replaced asset could fail with a "trade identifier not found" error.
* :bug:`1403` When removing an ethereum account that has liabilities, they should now also be removed from the dashboard and from the blockchain accounts view.
* :bug:`2998` If a new token is added in the rotki list of assets then the token detection cache is now invalidated so it will be detected when refreshing balances.
* :bug:`2999` If a binance withdrawal is missing the txId field rotki will now still be able to process it correctly.
* :bug:`2993` If a sell of FIAT for crypto is made, which is effectively a buy of crypto with FIAT, complaints about the source of funds should no longer be generated.
* :bug:`2994` Nexo users will be able to correctly import their information from a CSV file.

* :release:`1.17.1 <2021-05-26>`
* :bug:`2984` The notification background will now properly adjust for users using the application in light mode.
* :bug:`2982` Premium users of v1.17.0 who had DB syncing activated will now be able to open the app again.
* :bug:`2986` Users won't be affected by a login error at the moment of querying FTX when the keys are correct.

* :release:`1.17.0 <2021-05-25>`
* :feature:`2898` Users are now able to see the asset identifiers in the asset management view and replace one asset and all its occurrences with another.
* :feature:`2820` Users will now be able to select if they want to view graphs based at a 0 y-axis start instead of the minimum in the selected period.
* :feature:`2725` Users will now be able to view a small help dialog with the supported options for the date display format.
* :feature:`1902` Users can now modify the backend settings (e.g. data directory, log directory) through the application.
* :feature:`2584` Removed the option to anonymize the logs. Logs are off by default anyway and it was never possible to anonymize accurately and completely when activated so the setting was misleading.
* :feature:`47` Users can now add multiple accounts per supported exchange.
* :feature:`1881` Users can now access an about screen with information about the application.
* :feature:`1549` rotki premium users will now be able to switch to a dark mode and change the theme colors.
* :feature:`1674` Add experimental support for BlockFi imports using CSV files.
* :feature:`2224` Add experimental support for Nexo imports using CSV files.
* :feature:`2475` Withdrawals from Binance and Binance US will now have their fee correctly imported.
* :feature:`2803` Ethereum tokens that consist of underlying tokens will now see their price correctly fetched.
* :feature:`2844` Premium users will now be able to fetch their Uniswap v3 swaps.
* :feature:`2893` Users can now see if any of their addresses have CVX available to claim from the ConvexFinance airdrop.
* :feature:`2529` Crypto.com CSV import functionality has been updated to allow more types of entries.
* :bug:`2850` User will now see a consistent naming of exchanges across the application.
* :bug:`367` Fixed edge cases where some tasks would run for hours due to the absence of timeouts.
* :bug:`2875` Invalid ENS names should now provide a proper error when provided to rotki.
* :bug:`2888` Ledger actions selected to be ignored in the profit and loss report will now be correctly ignored.

* :release:`1.16.2 <2021-05-08>`
* :bug:`-` If a DeFi event provides zero amount of an asset to a user the PnL report should now work properly again.
* :bug:`2857` Users will now properly see their blockchain balances fetched when restoring to a new account using premium.
* :bug:`2818` Windows users will now be able to properly login after updating the assets.
* :bug:`2856` Users will properly see error messages when the account creation fails.
* :bug:`2851` Users should now see the external trades fetched first when visiting the trades page.
* :bug:`2835` Eth2 users with a very big number of validators should no longer get a 429 error.
* :bug:`2846` Premium users who create a new account with premium api credentials that have no saved DB in the server to sync with will have these credentials properly saved in the DB right after creation. At re-login the premium subscription should be properly recognized and the credentials should not need to be input again.
* :bug:`2821` Users will now be able to properly scroll through the asset when conflicts appear during the asset database upgrade.
* :bug:`2837` Binance US users will now be able to see the correct location for their trades and deposits/withdrawals. It should no longer be Binance. To reflect those changes Binance US data should be purged and then re-queried. To see how to purge data for an exchange look here: https://rotki.readthedocs.io/en/latest/usage_guide.html#purging-data
* :bug:`2819` Users using macOS will no longer be stuck at "connecting to backend".
* :bug:`865` Users will now be given an option to retry or terminate the application when communication with the backend fails.
* :bug:`2791` Updating assets database which adds customs assets already owned as officially supported should no longer get the DB in an inconsistent state.

* :release:`1.16.1 <2021-04-30>`
* :bug:`2811` ETH and WETH are now considered equivalent for cost basis and accounting purposes.
* :bug:`2794` Aave v1 data after block 12,152,920 should be now available. rotki switched to the new Aave v1 subgraph.
* :bug:`2781` From this version and on, attempting to open a new global DB with an older rotki version will not be allowed and the app will crash with an error message.
* :bug:`2773` Timestamps will be correctly read for trades in the Kraken exchange.
* :bug:`2775` Ambiguous FTX assets will now be properly recognized by rotki.
* :bug:`2767` Curve pool tokens will not be double counted in the dashboard balances.

* :release:`1.16.0 <2021-04-21>`
* :feature:`2671` rotki will now detect Adex V5 staked balances
* :feature:`2714` Add support for a3CRV Curve pool
* :feature:`2210` All price history caches are now moved to the global database. The price history sub-directory of the rotki data directory is now deleted. This should optimize price history querying and save disk space.
* :feature:`2551` Users will now be prompted with asset database updates if changes have happened to the supported rotki assets.
* :feature:`2520` Users can now properly clean cached data for Eth2 daily stats and deposits.
* :feature:`2564` Users can now easily access the documentation and other helpful links directly from the application.
* :feature:`-` Users will now get an error message if during the PnL report an acquisition date for a sold asset can't be found. Also if an action with an unknown token is processed. This way users will know that they need to manually add more data to rotki.
* :feature:`2338` The users can now optionally add a rate and rate asset when adding a ledger action.
* :feature:`-` The external trade fee and fee currency are now optional and the users can skip them when adding a trade.
* :feature:`929` Users can now select which rounding mode is used for displayed amounts via the frontend settings.
* :feature:`2620` Users will now be able to disable oracles per asset using the asset editor.
* :feature:`2602` Users will now have the erc20 token details (name, symbol, decimals) automatically filled when possible when they add new ethereum token assets.
* :feature:`2427` The visible row selection will now persist after a re-login. Changing the visible rows will now affect all the tables.
* :feature:`2452` Users will now be able to use a two-mode sorting functionality when sorting tables.
* :feature:`2547` Users can now easily access the documentation on how to find the CryptoCompare/CoinGecko identifiers in asset manager.
* :feature:`2156` Users can now customise the explorer pages used for each chain.
* :feature:`522` Users can connect to different backends from the frontend.
* :feature:`2513` Users can now add/edit/delete all types of assets, not only ethereum tokens.
* :feature:`2424` Users will now see a progress bar while the automatic update is downloading, and proper notification messages in case of failure.
* :feature:`2515` Users will now be able to navigate back from the assets page using a button.
* :feature:`1007` Coinbase exchange users will now be able to see asset conversions in their trade history.
* :feature:`1334` FTX users will now be able to see their balances and have their deposit/withdrawal/trade history taken into account during profit/loss calculation.
* :feature:`2332` Binance users will now be able to see their Binance Pool's assets in rotki.
* :feature:`2713` Support the ETH-C MakerDAO vault collateral type.
* :bug:`2699` Users will see that the frontend state will properly be cleared when purging data.
* :bug:`2626` Users will now properly see their specified date format when viewing various DeFi protocols and statistics.
* :bug:`2479` Users will now see a < (less than) symbol in front of any amount with trailing decimals when rounding upwards is used.
* :bug:`2610` Macos users will now be able to properly update every time using the auto-updater.
* :bug:`2628` Users will now see the correct total asset value when visiting an asset's detail page for a second time.
* :bug:`2524` Users will now not be able to delete assets from the Global DB if any account in the local system owns them.
* :bug:`2631` Balancer trades will now be displaying the correct trade rate, both in the trade history section but also in the exported CSV.
* :bug:`2633` User with incomplete deposits and withdrawals in Coinbase Pro will now be able to generate a profit/loss report.
* :bug:`2644` Balance query should no longer hang if the user gets rate limited by beaconcha.in and the rate limiting should now be properly handled.
* :bug:`2643` Beaconcha.in api key should now be properly used if given by the user
* :bug:`2614` Uniswap users should no longer have missing trades in their uniswap history.
* :bug:`2674` Coinbasepro should now also properly parse historical market trades and not only limit ones. Also all fills will be separately shown and not just the executed orders.
* :bug:`2656` Users of coinbase with a lot of assets or trades should now see all of them again. There should be no missing balances or trades thanks to a fix at query pagination.
* :bug:`2690` Eth2 stakers that have very recently deposited and don't have a validator index yet will now be handled properly and their balance should be shown.
* :bug:`2716` Users will now get a correct exported CSV file when a sell is matched with multiple acquisitions.
* :bug:`2738` Premium users won't see locations that have no balances in the statistics for value distribution by location.
* :bug:`2647` Disabling the tax-free period setting for a Profit/Loss report will now be reflected in the same rotki run without needing a restart.

* :release:`1.15.2 <2021-03-21>`
* :bug:`1996` Querying coinbasepro deposits and withdrawals should now be much faster thanks to using their new API endpoints.

* :release:`1.15.1 <2021-03-19>`
* :feature:`-` Add support for Norwegian Krone (NOK) as a fiat currency
* :feature:`-` Add support for New Taiwan Dollar (TWD) as a fiat currency
* :bug:`2603` Adding multiple comma separated ethereum accounts which contain duplicate entries will not double count the duplicate entry account tokens.
* :bug:`2577` Users will now be unable to accidentally open a second instance of the application.
* :bug:`2467` Trades with a rate of zero will no longer be possible. This prevents the profit and loss report from hanging and shows a notification if an entry with rate equal to zero is already in the database.
* :bug:`2532` Users will now see the percentage sign display in the same line when editing underlying tokens.
* :feature:`2507` Users can now delete imported trades and deposit/withdrawals from crypto.com via the purge data UI.
* :bug:`2530` Poloniex should no longer display phantom LEND balances in rotki.
* :bug:`2534` Aave v2 tokens not in Aave v1 should no longer have their balance double counted.
* :bug:`2539` The effects of adding/editing/removing a ledger actions will no longer be lost if rotki restarts right after the operation.
* :bug:`2541` Now cost basis will be correctly shown in the profit and loss report if the cost basis were calculated using ledger actions outside the report period.

* :feature:`-` Added support for the following tokens:

  - `xAAVEa (xAAVEa) <https://www.coingecko.com/en/coins/xaavea>`__
  - `xAAVEb (xAAVEb) <https://www.coingecko.com/en/coins/xaaveb>`__
  - `xINCHa (xINCHa) <https://www.coingecko.com/en/coins/xincha>`__
  - `xINCHb (xINCHb) <https://www.coingecko.com/en/coins/xinchb>`__
  - `xSNXa (xSNXa) <https://www.coingecko.com/en/coins/xsnxa>`__

* :release:`1.15.0 <2021-03-09>`
* :feature:`1492` Balancer protocol is now supported. Premium users can see their LP balances, swaps history and LP pool join/exits. Finally the balancer trades are now taken into account in the profit/loss report.
* :feature:`1519` Users can now add custom ethereum tokens to rotki. They can also add custom icons to any of those tokens or any other asset of rotki. Custom icons always take precedence.
* :feature:`916` Users will have the option to set an automatic balance refresh period.
* :feature:`2379` Premium users will now be able to see their daily ETH2 staking details, how much they gained in ETH and fiat value. Furthermore they will be able to take it into account in the PnL report.
* :feature:`2384` Users will now see their loopring balances on dashboard nested underneath the Ethereum balances.
* :feature:`1448` When querying trades, deposits and withdrawals the entries that have already been queried will now be instantly shown to the user, while waiting for the query of the latest entries to complete.
* :feature:`1799` Modules will now be dynamically activated/deactivated at the moment the user modifies the settings from the frontend. Restarts of the app will no longer be necessary.
* :feature:`2401` Balances in loopring will now be included in the balance snapshots.
* :bug:`2442` Users will now see their accounts sorted by name instead of address when they sort by account in the assets view.
* :bug:`2443` Users who have no balances in Kraken and try to add an API key will now be able to set it up properly.
* :bug:`2468` Users should no longer get an error when adding a real estate manual balance.
* :bug:`2517` Correctly map FTT to FTX token for Binance.

* :feature:`-` Added support for the following tokens:

  - `Quickswap (QUICK) <https://www.coingecko.com/en/coins/quick>`__
  - `AC Milan Fan Token (ACM) <https://www.coingecko.com/en/coins/ac-milan-fan-token>`__
  - `Bounce Token (AUCTION) <https://www.coingecko.com/en/coins/auction>`__
  - `DODO bird (DODO) <https://www.coingecko.com/en/coins/dodo>`__
  - `StaFi (FIS) <https://www.coingecko.com/en/coins/stafi>`__
  - `Frax Share (FXS) <https://www.coingecko.com/en/coins/frax-share>`__
  - `Phala (PHA) <https://www.coingecko.com/en/coins/pha>`__
  - `UniLend Finance Token (UFT) <https://www.coingecko.com/en/coins/unlend-finance>`__
  - `SOLBIT (SBT) <https://www.coingecko.com/en/coins/solbit>`__
  - `SMARTCREDIT Token (SMARTCREDIT) <https://www.coingecko.com/en/coins/smartcredit-token>`__
  - `TheFutbolCoin (TFC) <https://www.coingecko.com/en/coins/thefutbolcoin>`__
  - `Oraichain Token (ORAI) <https://www.coingecko.com/en/coins/oraichain-token>`__
  - `Bridge Oracle (BRG) <https://www.coingecko.com/en/coins/bridge-oracle>`__
  - `Lattice Token (LTX) <https://www.coingecko.com/en/coins/lattice-token>`__
  - `ZeroSwapToken (ZEE) <https://www.coingecko.com/en/coins/zeroswap>`__
  - `Mask Network (MASK) <https://www.coingecko.com/en/coins/mask-network>`__
  - `IDEAOLOGY (IDEA) <https://www.coingecko.com/en/coins/ideaology>`__
  - `SparkPoint (SRK) <https://www.coingecko.com/en/coins/sparkpoint>`__
  - `VesperToken (VSP) <https://www.coingecko.com/en/coins/vesper-finance>`__
  - `ZKs (ZKS) <https://www.coingecko.com/en/coins/zkswap>`__
  - `Unifty (NIF) <https://www.coingecko.com/en/coins/unifty>`__
  - `Polyient Games Governance Token (PGT) <https://www.coingecko.com/en/coins/polyient-games-governance-token>`__
  - `RARE.UNIQUE (RARE) <https://www.coingecko.com/en/coins/unique-one>`__
  - `UnFederalReserveToken (eRSDL) <https://www.coingecko.com/en/coins/unfederalreserve>`__
  - `Rari Governance Token (RGT) <https://www.coingecko.com/en/coins/rari-governance-token>`__
  - `Fuse Token (FUSE) <https://www.coingecko.com/en/coins/fuse-network-token>`__
  - `SportX (SX) <https://www.coingecko.com/en/coins/sportx>`__
  - `Rari Stable Pool Token (RSPT) <https://www.coingecko.com/en/coins/rari-stable-pool-token>`__

* :release:`1.14.2 <2021-02-24>`
* :bug:`2399` Users will now see a warning if the loopring module is not activated when adding an API key, and balances will be fetched automatically if it is.
* :bug:`2151` Users will now see the datetime picker properly displaying the selected date when editing ledger actions.
* :bug:`2405` Legacy bitcoin address balances and xpub derivation should now work properly again after blockchain.info decided to yolo change their api response format.
* :bug:`2400` Loopring balances should now be queried properly for users who own USDT.
* :bug:`2398` An edge case of Kucoin historical trade query parsing is fixed. So now even users with some specific ids in their trades will be able to query history properly for Kucoin.

* :feature:`-` Added support for the following tokens:

  - `Rai Reflex Index (RAI) <https://www.coingecko.com/en/coins/rai>`__
  - `PoolTogether (POOL) <https://www.coingecko.com/en/coins/pooltogether>`__
  - `Lotto (LOTTO) <https://www.coingecko.com/en/coins/lotto>`__
  - `FTX Token (FTT) <https://www.coingecko.com/en/coins/ftx-token>`__
  - `Akash Network (AKT) <https://www.coingecko.com/en/coins/akash-network>`__
  - `Dfinance (XFI) <https://www.coingecko.com/en/coins/dfinance>`__
  - `Maps.me Token (MAPS) <https://www.coingecko.com/en/coins/maps>`__
  - `xToken (XTK) <https://www.coingecko.com/en/coins/xtoken>`__
  - `Mobile Coin (MOB) <https://www.coingecko.com/en/coins/mobilecoin>`__

* :release:`1.14.1 <2021-02-17>`
* :bug:`2391` The signed version of the MacOS binary should now work properly for all users.

* :release:`1.14.0 <2021-02-16>`
* :feature:`1005` MacOS users will no longer get the dreaded "Can not open the app because developer is not verified" warning. rotki is now a verified apple developer.
* :feature:`2299` During a PnL report rotki should now also take into account for cost basis the assets gained from or used in DeFi.
* :feature:`2318` Users can now see if their accounts are eligible for the Curve CRV airdrop and POAP Delivery badges.
* :feature:`297` rotki now supports KuCoin. Users can see their balances and import trades, deposits and withdrawals from that exchange. They are also taken into account in the tax report.
* :feature:`1436` Users will now see any validation errors when adding manual balances under their respective inputs instead of a modal dialog.
* :feature:`2235` Loopring users will now be able to add their loopring api key to rotki and have it track all their loopring l2 balances.
* :feature:`2330` Users can now easily navigate to the respective pages by clicking the dashboard cards titles for manual balances, blockchain balances and exchange balances.
* :feature:`2237` Users can now choose which ledger actions are taken into account in the PnL report by customizing a setting. Two new ledger action types are added. Airdrop and Gift.
* :feature:`1794` Users who create a Profit and Loss report will now be able to see a cost basis calculation in the events of the report and in the exported trades.csv and all_events.csv
* :feature:`1001` Users will now be taken directly to the add dialog when pressing add Blockchain Address or Manual Balance on the dashboard.
* :feature:`276` Users can now click on the assets on the dashboard and other tables and see which accounts hold this asset.
* :feature:`295` When creating external trades, users will now have the trade rate automatically fetched when such a rate exists.
* :feature:`2240` Users now can select the supported assets from a dropdown when adding or editing external trades.
* :bug:`2228` AdEx claim events now always have the proper token (e.g. ADX, DAI) and usd value. Also rotki should no longer miss Adex withdrawal events.
* :bug:`2335` Users having sold BSV they got from holding BCH during the BCH -> BSV fork will now have its cost basis properly counted in the PnL report.
* :bug:`2360` Users of Binance who own ONE tokens will now have it properly mapped to harmony.
* :bug:`2293` Go through DeFi events before the queried PnL range during PnL report for a more complete calculation.

* :feature:`-` Added support for the following tokens:

  - `Gunthy Token (GUNTHY) <https://www.coingecko.com/en/coins/gunthy>`__
  - `Bao Finance Token (BAO) <https://www.coingecko.com/en/coins/bao-finance>`__
  - `Sora Token (XOR) <https://www.coingecko.com/en/coins/sora>`__
  - `Banano (BAN) <https://www.coingecko.com/en/coins/banano>`__
  - `Redfox labs token (RFOX) <https://www.coingecko.com/en/coins/redfox-labs>`__
  - `BoringDAO (BOR) <https://www.coingecko.com/en/coins/boringdao>`__
  - `BoringDAO BTC (oBTC) <https://www.coingecko.com/en/coins/boringdao-btc>`__
  - `Woo trade network (WOO) <https://www.coingecko.com/en/coins/wootrade-network>`__
  - `ACoconut (AC) <https://www.coingecko.com/en/coins/acoconut>`__
  - `DeFiner (FIN) <https://www.coingecko.com/en/coins/definer>`__
  - `pTokens LTC (pLTC) <https://www.coingecko.com/en/coins/ptokens-ltc>`__
  - `Huobi BTC (HBTC) <https://www.coingecko.com/en/coins/huobi-btc>`__
  - `Autonio (NIOX) <https://www.coingecko.com/en/coins/autonio>`__
  - `Ton Token (TON) <https://www.coingecko.com/en/coins/tontoken>`__
  - `QCAD Token (QCAD) <https://www.coingecko.com/en/coins/qcad>`__
  - `Rigo Token (GRG) <https://www.coingecko.com/en/coins/rigoblock>`__
  - `bZx Vesting Token (vBZRX) <https://www.coingecko.com/en/coins/bzx-vesting-token>`__
  - `Nest protocol (NEST) <https://www.coingecko.com/en/coins/nest-protocol>`__
  - `pTokens BTC (pBTC) <https://www.coingecko.com/en/coins/ptokens-btc>`__
  - `Dxdao token (DXD) <https://www.coingecko.com/en/coins/dxdao>`__
  - `Liquid staked Ether 2.0 (stETH) <https://www.coingecko.com/en/coins/lido-staked-ether>`__
  - `KuCoin Token (KCS) <https://www.coingecko.com/en/coins/kucoin-shares>`__
  - `Caspian Token (CSP) <https://www.coingecko.com/en/coins/caspian>`__
  - `DXChain Token (CSP) <https://www.coingecko.com/en/coins/dxchain>`__
  - `MultiVAC (MTV) <https://www.coingecko.com/en/coins/multivac>`__
  - `TurtleCoin (TRTL) <https://www.coingecko.com/en/coins/turtlecoin>`__
  - `Jarvis+ Coins (JAR) <https://www.coingecko.com/en/coins/jarvis>`__
  - `Cryptoindex 100 (CIX100) <https://www.coingecko.com/en/coins/cryptoindex-io>`__
  - `The Forbidden Forest (FORESTPLUS) <https://www.coingecko.com/en/coins/the-forbidden-forest>`__
  - `Bolt (BOLT) <https://www.coingecko.com/en/coins/bolt>`__
  - `SERO (SERO) <https://www.coingecko.com/en/coins/super-zero>`__
  - `Syntropy (NOIA) <https://www.coingecko.com/en/coins/noia-network>`__
  - `Dapp Token (DAPPT) <https://www.coingecko.com/en/coins/dapp-com>`__
  - `EOSForce (EOSC) <https://www.coingecko.com/en/coins/eosforce>`__
  - `Dero (DERO) <https://www.coingecko.com/en/coins/dero>`__
  - `Enecuum (ENQ) <https://www.coingecko.com/en/coins/enq-enecuum>`__
  - `Tokoin (TOKO) <https://www.coingecko.com/en/coins/toko>`__
  - `EMOGI Network (LOL) <https://www.coingecko.com/en/coins/emogi-network>`__
  - `Amino Intelligent Network (AMIO) <https://www.coingecko.com/en/coins/amino-network>`__
  - `Maxonrow (MXW) <https://www.coingecko.com/en/coins/maxonrow>`__
  - `Roobee (ROOBEE) <https://www.coingecko.com/en/coins/roobee>`__
  - `MAP Protocol (MAP) <https://www.coingecko.com/en/coins/marcopolo>`__
  - `Proof Of Liquidity (POL) <https://www.coingecko.com/en/coins/proof-of-liquidity>`__
  - `ARCS (ARX) <https://www.coingecko.com/en/coins/arcs>`__
  - `Newscrypto Coin (NWC) <https://www.coingecko.com/en/coins/newscrypto-coin>`__
  - `BetProtocolToken (BEPRO) <https://www.coingecko.com/en/coins/bet-protocol>`__
  - `Insolar (XNS) <https://www.coingecko.com/en/coins/ins-ecosystem>`__
  - `Perth Mint Gold Token (PMGT) <https://www.coingecko.com/en/coins/perth-mint-gold-token>`__
  - `ROAD (ROAD) <https://www.coingecko.com/en/coins/road>`__
  - `Alchemy (ACOIN) <https://www.coingecko.com/en/coins/alchemy>`__
  - `VI (VI) <https://www.coingecko.com/en/coins/vid>`__
  - `Zel (ZEL) <https://www.coingecko.com/en/coins/zelcash>`__
  - `Axe (AXE) <https://www.coingecko.com/en/coins/axe>`__
  - `digitalbits (XDB) <https://www.coingecko.com/en/coins/digitalbits>`__
  - `Sylo (SYLO) <https://www.coingecko.com/en/coins/sylo>`__
  - `WOM Token (WOM) <https://www.coingecko.com/en/coins/wom-token>`__
  - `LUKSO (LYXE) <https://www.coingecko.com/en/coins/lukso-token>`__
  - `Pazzi (PAZZI) <https://www.coingecko.com/en/coins/paparazzi>`__
  - `Energy Web Token (EWT) <https://www.coingecko.com/en/coins/energy-web-token>`__
  - `Waves Enterprise (WEST) <https://www.coingecko.com/en/coins/waves-enterprise>`__
  - `BNS Token (BNS) <https://www.coingecko.com/en/coins/bns-token>`__
  - `MiL.k (MLK) <https://www.coingecko.com/en/coins/milk>`__
  - `Safe Haven (SHA) <https://www.coingecko.com/en/coins/safe-haven>`__
  - `Effect.AI (EFX) <https://www.coingecko.com/en/coins/effect-ai>`__
  - `Velo (VELO) <https://www.coingecko.com/en/coins/velo>`__
  - `Burancy (BUY) <https://www.coingecko.com/en/coins/burency>`__
  - `Sentivate (SNTVT) <https://www.coingecko.com/en/coins/sentivate>`__
  - `dego.finance (DEGO) <https://www.coingecko.com/en/coins/dego-finance>`__
  - `Hyprr (uDOO) <https://www.coingecko.com/en/coins/howdoo>`__
  - `UBIX Network (UBX) <https://www.coingecko.com/en/coins/ubix-network>`__
  - `Comboos (COMB) <https://www.coingecko.com/en/coins/combo-2>`__
  - `ReapChain (REAP) <https://www.coingecko.com/en/coins/reapchain>`__
  - `TE-FOOD/TustChain (TONE) <https://www.coingecko.com/en/coins/te-food>`__
  - `Opacity (OPCT) <https://www.coingecko.com/en/coins/opacity>`__
  - `UpBots (UBXT) <https://www.coingecko.com/en/coins/upbots>`__
  - `ClinTex (CTI) <https://www.coingecko.com/en/coins/clintex-cti>`__
  - `BUX Token (BUX) <https://www.coingecko.com/en/coins/buxcoin>`__
  - `MoneySwap (MSWAP) <https://www.coingecko.com/en/coins/moneyswap>`__
  - `GoMoney2 (GOM2) <https://www.coingecko.com/en/coins/gomoney2>`__
  - `REVV (REVV) <https://www.coingecko.com/en/coins/revv>`__
  - `AlpaToken (ALPA) <https://www.coingecko.com/en/coins/alpaca>`__
  - `Hathor (HTR) <https://www.coingecko.com/en/coins/hathor>`__
  - `Hydra (HYDRA) <https://www.coingecko.com/en/coins/hydra>`__
  - `Ferrum Network Token (FRM) <https://www.coingecko.com/en/coins/ferrum-network>`__
  - `Props Token (PROPS) <https://www.coingecko.com/en/coins/props>`__
  - `Strong (STRONG) <https://www.coingecko.com/en/coins/strong>`__
  - `Trias Token (TRIAS) <https://www.coingecko.com/en/coins/trias>`__
  - `Alphacat (ACAT) <https://www.coingecko.com/en/coins/alphacat>`__
  - `Achain (ACT) <https://www.coingecko.com/en/coins/achain>`__
  - `BUMO (BU) <https://www.coingecko.com/en/coins/bumo>`__
  - `cVToken (CV) <https://www.coingecko.com/en/coins/carvertical>`__
  - `Decentralized Accessible Content Chain (DACC) <https://www.coingecko.com/en/coins/dacc>`__
  - `Constellation (DAG) <https://www.coingecko.com/en/coins/constellation-labs>`__
  - `DeepBrain Chain (DBC) <https://www.coingecko.com/en/coins/deepbrain-chain>`__
  - `Eden Coin (EDN) <https://www.coingecko.com/en/coins/edenchain>`__
  - `Electroneum (ETN) <https://www.coingecko.com/en/coins/electroneum>`__
  - `HPBCoin (HPB) <https://www.coingecko.com/en/coins/high-performance-blockchain>`__
  - `Kambria Token (KAT) <https://www.coingecko.com/en/coins/kambria>`__
  - `Master Contract Token Token (MCT) <https://www.coingecko.com/en/coins/master-contract-token>`__
  - `DeepOnion (ONION) <https://www.coingecko.com/en/coins/deeponion>`__
  - `THEKEY (TKY) <https://www.coingecko.com/en/coins/thekey>`__
  - `APY.Finance (APY) <https://www.coingecko.com/en/coins/apy-finance>`__
  - `NFTX (APY) <https://www.coingecko.com/en/coins/nftx>`__
  - `Litentry (LIT) <https://www.coingecko.com/en/coins/litentry>`__
  - `Prosper (PROS) <https://www.coingecko.com/en/coins/prosper>`__
  - `SafePal (SFP) <https://www.coingecko.com/en/coins/safepal>`__
  - `Vai (VAI) <https://www.coingecko.com/en/coins/vai>`__
  - `Finiko (FNK) <https://www.coingecko.com/en/coins/finiko>`__
  - `Harmony (ONE) <https://www.coingecko.com/en/coins/harmony>`__

* :release:`1.13.3 <2021-02-11>`
* :bug:`2342` Binance users should be able to query exchange balances again after Binance broke their api by adding "123" and "456" as test assets.

* :release:`1.13.2 <2021-02-07>`
* :bug:`2295` Bitstamp users should now get all trade amounts and fees properly detected.
* :bug:`2232` Bitstamp users should now be able to see all their deposit/withdrawals. It's recommended to purge all bitstamp data and re-query it for this to properly work.
* :bug:`1928` rotki premium DB sync will now work after entering api keys for the first time even without a restart.
* :bug:`2294` Do not count MakerDAO Oasis proxy assets found by the DeFi SDK as it ends up double counting makerDAO vault deposits.
* :bug:`2287` rotki encrypted DB upload for premium users should now respect the user setting.

* :feature:`-` Added support for the following tokens:

  - `Aragon v2 (ANT) <https://www.coingecko.com/en/coins/aragon>`__
  - `Indexed Finance - NDX Token (NDX) <https://www.coingecko.com/en/coins/indexed-finance>`__
  - `Indexed Finance - DEFI5 (DEFI5) <https://www.coingecko.com/en/coins/defi-top-5-tokens-index>`__
  - `Indexed Finance - CC10 (CC10) <https://www.coingecko.com/en/coins/cryptocurrency-top-10-tokens-index>`__
  - `PieDAO Yearn Ecosystem Pie (YPIE) <https://www.coingecko.com/en/coins/piedao-yearn-ecosystem-pie>`__

* :release:`1.13.1 <2021-02-04>`
* :bug:`2222` Users who have funds in a DeFi Saver smart wallet will now be also able to see their liabilities in said wallet.
* :bug:`2249` Users will now properly see the prices of new assets reflected on the dashboard when adding manual balances.
* :bug:`2258` Users should now see the proper asset price, without rounding errors, for entries of the display asset.
* :feature:`-` Add support for Swedish Krona (SEK) as a fiat currency.
* :bug:`2267` DeFi events PnL CSV now properly includes the sign in the PnL column and also includes an extra column with the relevant transaction hashes and an optional note explaining more about the event.
* :bug:`2273` CREAM icon and price should now be shown correctly.
* :bug:`2261` Users who had STX in Binance should now see it mapped properly to blockstack and not stox.
* :bug:`-` Users will now see the total worth contained in the card for bigger amounts.
* :bug:`2239` Amounts in the dashboard should now appear in single line for users.
* :bug:`2244` Fix edge case where using a cryptocompare api key could result in the all coins endpoint to error if no cache already existed.
* :bug:`2215` Ledger action CSV export now contains identifier and not asset name.
* :bug:`2223` Manual balances with the blockchain tag will no longer be duplicated in the dashboard and blockchain account balances.

* :feature:`-` Added support for the following tokens:

  - `FOX Token (FOX) <https://www.coingecko.com/en/coins/fox-token>`__
  - `Experty Wisdom Token (WIS) <https://www.coingecko.com/en/coins/experty-wisdom-token>`__
  - `aleph.im v2 (ALEPH) <https://www.coingecko.com/en/coins/aleph-im>`__
  - `Perpetual Protocol (PERP) <https://www.coingecko.com/en/coins/perpetual-protocol>`__
  - `Name Change Token (NCT) <https://www.coingecko.com/en/coins/name-changing-token>`__
  - `Archer DAO Governance Token (ARCH) <https://www.coingecko.com/en/coins/archer-dao-governance-token>`__
  - `Starname (IOV) <https://www.coingecko.com/en/coins/starname>`__
  - `ASSY PowerIndex (ASSY) <https://www.coingecko.com/en/coins/assy-index>`__

* :release:`1.13.0 <2021-01-29>`
* :feature:`-` Add support for Singapore Dollar (SGD) as a fiat currency.
* :feature:`2022` Users can now see if their accounts are eligible for the Lido LDO airdrop.
* :feature:`2105` Users can now see if their accounts are eligible for the Furucombo COMBO airdrop.
* :feature:`2143` You can now add Bitcoin addresses by ENS name. Simply use an ENS name in the BTC address field and if it can be resolved it will be appended to the tracked accounts.
* :feature:`-` Add support for the following new MakerDAO vault collaterals: UNI, GUSD, RENBTC, AAVE.
* :feature:`1773` Users with funds in a DeFi saver smart wallet will have them included in rotki's balances.
* :feature:`2181` Users can now force creation of a price oracle's cache (cryptocompare) and also delete and inspect it.
* :feature:`1228` Users can see the current asset price of each asset on the dashboard and on the blockchain balances.
* :feature:`2053` Users can now refresh the asset prices on demand.
* :feature:`2188` When adding/editing ledger actions or trades, users can now specify datetime to seconds precision.
* :feature:`2131` Users can now customize the order of the price oracles used by rotki. For example set Coingecko as the first option for requesting prices and Cryptocompare as the fallback one.
* :feature:`2177` Users now will see a an error screen instead of a notification when there is an issue during the profit and loss report generation.
* :feature:`2174` Users can now delete all saved data of any of the supported modules.
* :feature:`-` The profit/loss report generation should now see a lot of improvements in regards to its speed.
* :feature:`2032` You can now add Kusama addresses by ENS name. Simply use an ENS name in the KSM address field and if it can be resolved it will be appended to the tracked accounts.
* :feature:`2146` Date format will now respect user choice in CSV export, logging output and other backend related locations. Also adding a new option to control whether those dates should be displayed/exported in local or UTC time.
* :feature:`2159` Users now won't see empty tables for blockchains without accounts.
* :feature:`2155` Users can now additionally filter the uniswap liquidity pools using a pool filter.
* :feature:`1865` Users will now see an explanation of the current stage of the profit/loss report's progress along with the completion percentage.
* :feature:`2158` Add support for all current Aaave v2 aTokens. Users will now be able to see them in their dashboard.
* :bug:`2117` Users can now properly dismiss notifications with long tiles, or dismiss all the pending notifications at once.
* :bug:`2024` Multiple crypto.com csv import debited entries with same timestamp will be handled correctly.
* :bug:`2135` Users will now properly see the correct accounting settings when creating a profit/loss report.
* :bug:`2168` Bitcoin.de users will now be able to properly import IOTA trades.
* :bug:`2175` Bittrex users with deposits/withdrawals of some edge case assets will now be able to properly process them.

* :feature:`-` Added support for the following tokens:

  - `MUST (Cometh) <https://www.coingecko.com/en/coins/must>`__
  - `StakeDao Token (SDT) <https://www.coingecko.com/en/coins/stake-dao>`__
  - `Digg token (DIGG) <https://www.coingecko.com/en/coins/digg>`__
  - `Edgeware (EDG) <https://www.coingecko.com/en/coins/edgeware>`__
  - `PieDAO Balanced Crypto Pie (BCP) <https://www.coingecko.com/en/coins/piedao-balanced-crypto-pie>`__
  - `PieDAO DEFI++ (DEFI++) <https://www.coingecko.com/en/coins/piedao-defi>`__
  - `PieDAO DEFI Small Cap (DEFI+S) <https://www.coingecko.com/en/coins/piedao-defi-small-cap>`__
  - `PieDAO DEFI Large Cap (DEFI+L) <https://www.coingecko.com/en/coins/piedao-defi-large-cap>`__
  - `PieDAO BTC++ (BTC++) <https://www.coingecko.com/en/coins/piedao-btc>`__
  - `AllianceBlock Token (ALBT) <https://www.coingecko.com/en/coins/allianceblock>`__
  - `Shroom.finance (SHROOM) <https://www.coingecko.com/en/coins/shroom-finance>`__
  - `Invictus Hyperoin Fund (IHF) <https://www.coingecko.com/en/coins/invictus-hyperion-fund>`__
  - `Flow - Dapper labs (FLOW) <https://www.coingecko.com/en/coins/flow>`__
  - `Lido DAO (LDO) <https://www.coingecko.com/en/coins/lido-dao>`__
  - `Binance Beacon ETH (BETH) <https://www.cryptocompare.com/coins/beth/overview>`__
  - `DeXe (DEXE) <https://www.coingecko.com/en/coins/dexe>`__
  - `Trust Wallet Token (TWT) <https://www.coingecko.com/en/coins/trust-wallet-token>`__
  - `Meaconcash (MCH) <https://www.coingecko.com/en/coins/meconcash>`__
  - `3X Short Chainlink Token (LINKBEAR) <https://www.coingecko.com/en/coins/3x-short-chainlink-token>`__
  - `3X Long Chainlink Token (LINKBULL) <https://www.coingecko.com/en/coins/3x-long-chainlink-token>`__
  - `3X Short Litecoin Token (LTCBEAR) <https://www.coingecko.com/en/coins/3x-short-litecoin-token>`__
  - `3X Long Litecoin Token (LTCBULL) <https://www.coingecko.com/en/coins/3x-long-litecoin-token>`__
  - `3X Short Stellar Token (XLMBEAR) <https://www.coingecko.com/en/coins/3x-short-stellar-token>`__
  - `3X Long Stellar Token (XLMBULL) <https://www.coingecko.com/en/coins/3x-long-stellar-token>`__

* :release:`1.12.2 <2021-01-18>`
* :bug:`2120` rotki should now display the action datetime when editing a ledger action.
* :bug:`2116` Kusama user balance query should now work properly in all cases.
* :bug:`2113` Iconomi exchange users should now no longer get an error when pulling deposits/withdrawals history

* :release:`1.12.1 <2021-01-16>`
* :bug:`-` Fix the problem introduced with rotki v1.12.0 for OSX users that made them unable to run the app.

* :release:`1.12.0 <2021-01-16>`
* :feature:`968` rotki will now run some heavier tasks periodically in the background to alleviate the alleviate the pressure from big tasks like the profit loss report. These tasks for now are: exchanges trades query, ethereum transactions query, cryptocompare historical price queries and xpub address derivation.
* :feature:`2015` Users can now selectively ignores trades, deposits/withdrawals, ethereum transactions and ledger actions in the accounting processing of the profit loss report.
* :feature:`1920` rotki now supports addition of a custom Kusama endpoint.
* :feature:`1662` Users are now able to manually input ledger actions such as Income, Donation, Loss, Expense, Dividends Income.
* :feature:`1866` The tax report is now named Profit and Loss Report.
* :feature:`1466` The account label is now renamed to account name.
* :bug:`1140` Users will now see the account balances sorted by label instead of hex when sorting the account column.
* :feature:`1919` rotki now supports Kusama blockchain. Users can import their Kusama addresses and see their KSM balances.
* :feature:`1792` Users should now be able to see the accounting settings used when generating a tax report.
* :bug:`1946` There should no longer be a non 0-100 percentage in the tax report during the progress report.
* :bug:`2040` Balance snapshotting should now work again for Bitfinex and Bitstamp users.
* :feature:`2056` Users can now control whether a profit loss report in a certain time range is allowed to go further in the past to calculate the real cost basis of assets or not. By default this setting is on.
* :feature:`2008` Users can now search for a currency in the currency selection UI.
* :bug:`2006` Users will now properly see all accounts selected as a hint when no account is selected in airdrops.
* :bug:`2023` Crypto.com is now properly not displayed as a connectable exchange.
* :feature:`1950` Users can now use a predefined yearly or quarterly range when generating a tax report.
* :bug:`2013` Show correct fee currency for Bitfinex trades.
* :feature:`991` Add Bitcoin.de exchange.
* :feature:`629` Add ICONOMI exchange. Balances and trades of single assets can be imported.
* :bug:`1759` Xpub address derivation after restart of the app from an existing xpub should no longer miss addresses
* :bug:`2047` Fix balances query for users of Binance.us

* :feature:`-` Added support for the following tokens:

  - `Energi (NRG) <https://www.coingecko.com/en/coins/energi>`__
  - `Exeedme (XED) <https://www.coingecko.com/en/coins/exeedme>`__
  - `Terra Virtua Kolect (TVK) <https://www.coingecko.com/en/coins/terra-virtua-kolect>`__
  - `Celsius network token (CEL) <https://www.coingecko.com/en/coins/celsius-network-token>`__
  - `BTC Standard Hashrate Token (BTCST) <https://www.coingecko.com/en/coins/btc-standard-hashrate-token>`__
  - `Stakenet (XSN) <https://www.coingecko.com/en/coins/stakenet>`__
  - `e-Radix (EXRD) <https://www.coingecko.com/en/coins/e-radix>`__
  - `BitcoinV (BTCV) <https://www.coingecko.com/en/coins/bitcoinv>`__
  - `GOLD (GOLD) <https://www.coingecko.com/en/coins/gold>`__
  - `KOK Coin (KOK) <https://www.coingecko.com/en/coins/kok-coin>`__
  - `Oxen (OXEN) <https://www.coingecko.com/en/coins/oxen>`__
  - `Carry (CRE) <https://www.coingecko.com/en/coins/carry>`__
  - `Alchemy Pay (ACH) <https://www.coingecko.com/en/coins/alchemy-pay>`__
  - `Basis Cash (BAC) <https://www.coingecko.com/en/coins/basis-cash>`__
  - `BarnBridge (BOND) <https://www.coingecko.com/en/coins/barnbridge>`__
  - `Furucombo (COMBO) <https://www.coingecko.com/en/coins/furucombo>`__
  - `Cudos (CUDOS) <https://www.coingecko.com/en/coins/cudos>`__
  - `Tokenlon (LON) <https://www.coingecko.com/en/coins/tokenlon>`__
  - `pBTC35A (PBTC35A) <https://www.coingecko.com/en/coins/pbtc35a>`__
  - `KeeperDAO (ROOK) <https://www.coingecko.com/en/coins/keeperdao>`__

* :release:`1.11.0 <2020-12-30>`
* :bug:`1929` Premium users will be able to see the proper balances after a force pull.
* :feature:`438` rotki now supports Bitfinex. Users can see their balances and import trades, deposits and withdrawals from that exchange. They are also taken into account in the tax report.
* :feature:`-` Users can now save the login username across sessions.
* :feature:`972` Users can now see which aidrops any of their addresses is eligible for.
* :feature:`1949` All time pickers now use a 24h format to avoid user confusion.
* :feature:`1961` Users can configure the BTC address derivation gap limit.
* :feature:`1955` Users can now set their main currency to Swiss Franc.
* :feature:`1270` Users can now set their main currency to ETH or BTC and see everything in that currency. Their net value, the valueof each asset they own, value of each trade, event e.t.c.
* :feature:`1515` rotki now supports Binance US. Users can see their balances and import trades, deposits and withdrawals from that exchange. They are also taken into account in the tax report.
* :feature:`1838` Allow users to input a beaconcha.in API key for better request limits: https://beaconcha.in/pricing
* :feature:`-` Support MANA and AAVE in Kraken and also detect staked Kava and ETH2.
* :bug:`1974` Binance USDT margined future and Coin margined future balances should now be visible in rotki.
* :bug:`1969` Users who were using open nodes only and were seeing an out of gas error during defi balances query, should be able to query defi balances properly again.
* :bug:`1287` Querying bitmex balances should now work properly again.
* :feature:`1515` rotki now supports Binance US. Users can see their balances and import trades, deposits and withdrawals from that exchange. They are also taken into account in the tax report.
* :bug:`1916` Querying bitstamp trades should now work properly again.
* :bug:`1917` Users can now properly login if they input the username after the password.
* :bug:`1953` Show a proper error when a user inputs an invalid xpub or derivation path.
* :bug:`1983` Balances and historical accounting for y3Crv vault should work properly again.
* :bug:`1998` Uniswap liquidity providing events Profit and loss should now show proper signs.

* :feature:`-` Added support for the following tokens:

  - `Mirror Protocol Token (MIR) <https://www.coingecko.com/en/coins/mirror-protocol>`__
  - `300Fit Network (FIT) <https://www.coingecko.com/en/coins/300fit>`__
  - `Power Index Pool Token (PIPT) <https://www.coingecko.com/en/coins/power-index-pool-token>`__
  - `Yearn Ecosystem Token Index (YETI) <https://www.coingecko.com/en/coins/yearn-ecosystem-token-index>`__
  - `Graph Token (GRT) <https://www.coingecko.com/en/coins/the-graph>`__
  - `1INCH Token (1INCH) <https://www.coingecko.com/en/coins/1inch>`__
  - `Stobox Token (STBU) <https://www.coingecko.com/en/coins/stobox-token>`__
  - `Binance VND (VND) <https://www.coingecko.com/en/coins/binance-vnd>`__
  - `Juventus Fan Token (JUV) <https://www.coingecko.com/en/coins/juventus-fan-token>`__
  - `Paris Saint-Germain Fan Token (PSG) <https://www.coingecko.com/en/coins/paris-saint-germain-fan-token>`__
  - `AC eXchange Token (ACXT) <https://www.coingecko.com/en/coins/ac-exchange-token>`__
  - `Validity Token (VAL) <https://www.coingecko.com/en/coins/validity>`__
  - `Empty Set Dollar (ESD) <https://www.coingecko.com/en/coins/empty-set-dollar>`__
  - `TrueFi Trust Token (TRU) <https://www.coingecko.com/en/coins/truefi>`__
  - `Mettalex (MTLX) <https://www.coingecko.com/en/coins/mettalex>`__
  - `Okex OKB Token (OKB) <https://www.coingecko.com/en/coins/okb>`__
  - `Callisto Network (CLO) <https://www.coingecko.com/en/coins/callisto-network>`__
  - `Ultra (UOS) <https://www.coingecko.com/en/coins/ultra>`__
  - `Metaverse ETP (ETP) <https://www.coingecko.com/en/coins/metaverse-etp>`__
  - `EOSDT (EOSDT) <https://www.coingecko.com/en/coins/eosdt>`__
  - `Tether EUR (EURT) <https://www.cryptocompare.com/coins/eurt/overview>`__
  - `LiquidApps (DAPP) <https://www.coingecko.com/en/coins/liquidapps>`__
  - `V.SYSTEMS (VSYS) <https://www.coingecko.com/en/coins/v-systems>`__
  - `Dragon Token (DT) <https://www.coingecko.com/en/coins/dragon-token>`__
  - `CryptoFranc (XCHF) <https://www.coingecko.com/en/coins/cryptofranc>`__
  - `Tether Gold (XAUT) <https://www.coingecko.com/en/coins/tether-gold>`__
  - `XinFin (XDC) <https://www.coingecko.com/en/coins/xinfin>`__
  - `RIF Token (RIF) <https://www.coingecko.com/en/coins/rif-token>`__
  - `ZB Token (ZB) <https://www.coingecko.com/en/coins/zb-token>`__
  - `RING X PLATFORM (RINGX) <https://www.coingecko.com/en/coins/ring-x-platform>`__
  - `Hermez Network (HEZ) <https://www.coingecko.com/en/coins/hermez-network>`__
  - `Essentia (ESS) <https://www.coingecko.com/en/coins/essentia>`__
  - `Native Utility Token (NUT) <https://www.coingecko.com/en/coins/native-utility-token>`__
  - `LEO Token (LEO) <https://www.coingecko.com/en/coins/leo-token>`__
  - `Utopia Genesis Foundation (UOP) <https://www.coingecko.com/en/coins/utopia-genesis-foundation>`__
  - `Rebitcoin (RBTC) <https://www.coingecko.com/en/coins/rebitcoin>`__
  - `Data Transaction Token (XD) <https://www.coingecko.com/en/coins/data-transaction-token>`__
  - `Ether Kingdoms Token (IMP) <https://www.coingecko.com/en/coins/ether-kingdoms-token>`__
  - `Renrenbit (RRB) <https://www.coingecko.com/en/coins/renrenbit>`__
  - `Tether CNH (CNHT) <https://www.cryptocompare.com/coins/cnht/overview>`__
  - `Xriba (XRA) <https://www.coingecko.com/en/coins/xriba>`__
  - `BTSE Token (BTSE) <https://www.coingecko.com/en/coins/btse-token>`__
  - `Tornado Cash Token (TORN) <https://www.coingecko.com/en/coins/tornado-cash>`__
  - `Reef Finance (REEF) <https://www.coingecko.com/en/coins/reef-finance>`__
  - `AS Roma Fan Token (ASR) <https://www.coingecko.com/en/coins/as-roma-fan-token>`__
  - `OG Fan Token (OG) <https://www.coingecko.com/en/coins/og-fan-token>`__

* :release:`1.10.1 <2020-12-16>`
* :bug:`-` This release should fix the "Failed at database upgrade from version 21 to 22: arguments should be given at the first instantiation" error
* :bug:`-` Do not double count Binance lending balances and don't show Zero balances in binance futures and lending.

* :release:`1.10.0 <2020-12-15>`
* :feature:`1681` AdEx protocol is now supported. Staking balances, events and APR are now detected by rotki for premium users.
* :feature:`1869` Vote-escrowed CRV will now be auto-detected for Curve.fi users. The amount shown will be the total locked CRV for vote-escrow.
* :feature:`114` Added a frontend-only setting to make the periodic query of the client customizable. The allowed range of values is from 5 seconds to 3600 seconds.
* :feature:`1753` Users can now filter the DEX trades by address and date range.
* :feature:`1858` rotki detects staked ETH2 balances in Kraken
* :feature:`1810` Users can now set the default timeframe for the net worth graph. The selected timeframe now persist when navigating from and to the dashboard.
* :feature:`436` rotki now supports Bitstamp. Users can see their balances and import trades, deposits and withdrawals from that exchange. They are also taken into account in the tax report.
* :feature:`1611` rotki can now import data and download the tax report csv when running in the browser.
* :feature:`1851` Eth2 deposits will now be queried separately from Eth2 staking details in the Eth2 staking view. As a result the loading of the staking view for Eth2 is faster. Also usd_value should now properly appear with the historical ETH value for each deposit.
* :feature:`1413` Users can now refresh their manual balances from the dashboard.
* :feature:`176` Add an accounting setting to make asset movements fees (deposits/withdrawals to/from exchanges) inclusion in the profit loss report configurable.
* :feature:`1840` Better handling double crypto.com entries (dust_conversion, swap, ...) from csv export. Also crypto.com imported trades and asset movements now appear in the history UI component
* :feature:`1605` User funds in Binance's futures wallet should now also be included in rotki.
* :feature:`1776` User funds in Binance's lending/saving wallet should now also be included in rotki.
* :bug:`1834` Users will not have to close the add account dialog manually while the newly added account balances are queried.
* :bug:`1671` Users will now see the amounts earned on aave lending aggregated per asset.
* :bug:`1868` Binance SOL token is now properly mapped to Solana.
* :bug:`1849` Binance queries should no longer randomly fail with invalid signature.
* :bug:`1846` AMPL token balance should no longer be double counted.
* :bug:`1888` Detect balances of Eth2 deposits that are pending and the validator is not yet active in the beacon chain
* :bug:`1887` The Eth2 validator index should not be incorrectly shown for some users.
* :bug:`-` Ocean protocol token balances should now be properly detected after the token migration.

* :feature:`-` Added support for the following tokens:

  - `Vote-escrowed CRV (veCRV) <https://etherscan.io/address/0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2>`__
  - `Index cooperative (INDEX) <https://www.coingecko.com/en/coins/index-cooperative>`__
  - `Amp (AMP) <https://www.coingecko.com/en/coins/amp>`__
  - `Harvest finance GRAIN token (GRAIN) <https://www.coingecko.com/en/coins/grain-token>`__
  - `Panvala pan token (PAN) <https://www.coingecko.com/en/coins/panvala-pan>`__
  - `Cover Protocol (COVER) <https://www.coingecko.com/en/coins/cover-protocol>`__
  - `dForce token (DF) <https://www.coingecko.com/en/coins/dforce-token>`__
  - `Skale token (SKL) <https://www.coingecko.com/en/coins/skale>`__
  - `Aidos Kuneen (ADK) <https://www.coingecko.com/en/coins/aidos-kuneen>`__
  - `Firo (FIRO) <https://www.coingecko.com/en/coins/firo>`__
  - `Galaxy Network (GNC) <https://www.coingecko.com/en/coins/galaxy-network>`__
  - `Social Good (SG) <https://www.coingecko.com/en/coins/socialgood>`__
  - `NuCypher (NU) <https://www.coingecko.com/en/coins/nucypher>`__
  - `Badger DAO (BADGER) <https://www.coingecko.com/en/coins/badger-dao>`__
  - `API3 (API3) <https://www.coingecko.com/en/coins/api3>`__
  - `Secret (SCRT) <https://www.coingecko.com/en/coins/secret>`__
  - `Spartan Protocol Token (SPARTA) <https://www.coingecko.com/en/coins/spartan-protocol-token>`__

* :release:`1.9.2 <2020-12-12>`
* :bug:`1896` Provide a temporary fix for the breaking change that the Graph introduced into their schemas that breaks all current python implementations. Users should no longer see _SubgraphErrorPolicy_! errors.

* :release:`1.9.1 <2020-11-29>`
* :feature:`1716` rotki can now also query data from the following ethereum open nodes:
  - 1inch
  - my ether walet
  - cloudflare-eth
  - linkpool
* :bug:`1777` Free users will now be able to load uniswap LP balances properly again.
* :bug:`1726` When querying Compound history for COMP claimed around the start of COMP issuance, zero price warnings should no longer be emitted.
* :feature:`1804` Premium users: Eth2 staking balances (along with what is gained via staking) will now be shown along with an APR estimation of the gains by staking.
* :feature:`369` Users can now import multiple addresses at once.
* :feature:`-` Users can now select predefined display date ranges for the premium statistics.
* :bug:`1801` Users that have the uniswap module deactivated will now see a proper message about the module status instead of a loading page.
* :bug:`1798` Log level settings now are properly saved and the users are not required to set them on every run.
* :bug:`1785` Inform the user when they try to setup Bittrex with their system clock not in sync.
* :bug:`1761` Retry GraphQL requests when the API server fails.
* :bug:`1809` Token balances should now always be saved in the balances snapshot. Also an edge case that rarely caused the ethereum balances to be queried twice should be now fixed.
* :bug:`1803` After 25/11/2020 Compound's claimable COMP stopped appearing in the app due to a change in a smart contract we depend on. This has now been fixed and they should be detected properly again.
* :bug:`1416` Request Binance deposits & withdraws using a 90 days window.
* :bug:`1787` After 24/11/2020 some Infura users started getting a "query returned more than 10000 results" error when querying their balances. This should no longer happen.
* :feature:`1774` Users now will only see the dashboard liabilities if there are liabilities to show.
* :feature:`1745` Users can now delete multiple blockchain accounts at once.
* :bug:`1778` Uniswap pool balances will now only be loaded when the user navigates to the Liquidity pools screen.

* :feature:`-` Added support for the following tokens:

  - `renBCH (renBCH) <https://www.coingecko.com/en/coins/renbch>`__
  - `renZEC (renZEC) <https://www.coingecko.com/en/coins/renzec>`__
  - `Swerve.fi DAI/USDC/USDT/TUSD (swUSD) <https://www.coingecko.com/en/coins/swusd>`__
  - `Golem (GLM) <https://www.coingecko.com/en/coins/golem>`__
  - `Hegic (HEGIC) <https://www.coingecko.com/en/coins/hegic>`__
  - `Prometeus (PROM) <https://www.coingecko.com/en/coins/prometeus>`__
  - `88mph (MPH) <https://www.coingecko.com/en/coins/88mph>`__
  - `zLOT (ZLOT) <https://www.coingecko.com/en/coins/zlot>`__
  - `tBTC (TBTC) <https://www.coingecko.com/en/coins/tbtc>`__
  - `Cornichon (CORN) <https://www.coingecko.com/en/coins/cornichon>`__

* :release:`1.9.0 <2020-11-20>`
* :feature:`717` Uniswap v2 LP balances are now detected by rotki. Faster balance queries, swaps history and LP events history is also supported for premium users. Finally uniswap trades are now taken into account in the profit/loss report for premium users.
* :bug:`1664` Properly convert the given xpub to ypub if P2SH_P2WPKH and zpub if WPKH. This should address the problem of importing some types of xpubs for some users.
* :bug:`1740` SNX token and some other token balances should no longer be double counted.
* :feature:`1724` YFI and BAL are now supported as collateral for makerdao vaults.
* :feature:`1694` Users are now able to track their ETH deposited in Eth2 beacon chain. Premium users can see more details about the activity and their staking gains in the staking menu.
* :feature:`1660` Users will now be able to see and edit labels and tags for xpub addresses.
* :feature:`1227` Users can now see a net worth graph on the dashboard.
* :feature:`1400` Liabilities are now shown on the dashboard and subtracted from the total net value.
* :bug:`1668` Refreshing BTC balances now, will not clear any other assets from the state.
* :bug:`1669` Users will now see a loading indicator when balances are loading and proper non-zero values after loading.
* :bug:`1678` Selected type will now not be ignored, when adding an xpub that already contains an x/y/zpub prefix.
* :bug:`1686` Compound historical interest profit is now shown correctly if theuser still has assets locked in compound.
* :feature:`1414` Users will now be shown only the available locations when filtering trades.

* :feature:`-` Added support for the following tokens:

  - `Synthetix sBTC (sBTC) <https://www.coingecko.com/en/coins/sbtc>`__
  - `Synthetix sETH (sETH) <https://www.coingecko.com/en/coins/seth>`__
  - `Synthetix sLINK (sLINK) <https://www.coingecko.com/en/coins/slink>`__
  - `Synthetix sXAU (sXAU) <https://www.coingecko.com/en/coins/sxau>`__
  - `Synthetix sXAG (sXAG) <https://www.coingecko.com/en/coins/sxag>`__
  - `Synthetix iBTC (iBTC) <https://www.coingecko.com/en/coins/ibtc>`__
  - `Synthetix iETH (iETH) <https://www.coingecko.com/en/coins/ieth>`__
  - `Aave Interest bearing Uniswap (aUNI) <https://etherscan.io/address/0xB124541127A0A657f056D9Dd06188c4F1b0e5aab>`__
  - `Blockstack (STX) <https://www.coingecko.com/en/coins/blockstack>`__
  - `Axie Infinity Shard (AXS) <https://www.coingecko.com/en/coins/axie-infinity>`__
  - `Bitcoin ABC (BCHA) <https://www.coingecko.com/en/coins/bitcoin-cash-abc>`__
  - `Binance leveraged token BCHDOWN (BCHDOWN) <https://www.cryptocompare.com/coins/bchdown/overview>`__
  - `Binance leveraged token BCHUP (BCHUP) <https://www.cryptocompare.com/coins/bchup/overview>`__
  - `Frontier Token (FRONT) <https://www.coingecko.com/en/coins/frontier>`__
  - `HARD Protocol (HARD) <https://www.coingecko.com/en/coins/hard-protocol>`__
  - `Keep3rV1 (KP3R) <https://www.coingecko.com/en/coins/keep3rv1>`__
  - `Oasis Network (ROSE) <https://www.coingecko.com/en/coins/oasis-network>`__
  - `Small Love Potion (SLP) <https://www.coingecko.com/en/coins/small-love-potion>`__
  - `Stratis (STRAX) <https://www.coingecko.com/en/coins/stratis>`__
  - `Unifi Protocol DAO (UNFI) <https://www.coingecko.com/en/coins/unifi-protocol-dao>`__
  - `Akoin (AKN) <https://www.coingecko.com/en/coins/akoin>`__
  - `Camp (CAMP) <https://www.cryptocompare.com/coins/camp/overview>`__
  - `Gleec Coin (GLEEC) <https://www.coingecko.com/en/coins/gleec-coin>`__
  - `NerveNetwork (NVT) <https://www.coingecko.com/en/coins/nervenetwork>`__
  - `ShareToken (SHR) <https://www.coingecko.com/en/coins/sharetoken>`__

* :release:`1.8.3 <2020-10-30>`
* :bug:`1636` Users running earlier OSX versions than Catalina can again start the application properly.
* :bug:`1635` Application will now continue running when changing log level on Windows.
* :feature:`1642` Force pull/push buttons for premium sync are now accessible in the floppy disk icon on the toolbar.
* :bug:`1639` Native segwit xpubs will now properly query and display the balances of their derived addresses. rotki switched to using blockstream's API instead of blockcypher for native segwit addresses.
* :bug:`1638` Balances displayed in dashboard cards should now be properly sorted by value in descending order.
* :bug:`-` If the DB has not been uploaded in this run of rotki, the last upload time indicator now shows the last time data was uploaded and not "Never".
* :bug:`1641` rotki only accepts derivation paths in the form of m/X/Y/Z... where ``X``, ``Y`` and ``Z`` are integers. Anything else is not processable and invalid. We now check that the given path is valid and reject the addition if not. Also the DB is upgraded and any xpubs with such invalid derivation path are automatically deleted.
* :bug:`1637` Loading ethereum transactions on the UI should work properly again now

* :feature:`-` Added support for the following tokens:

  - `Compound Collateral (cCOMP) <https://www.coingecko.com/en/coins/ccomp>`__
  - `Certik (CTK) <https://www.coingecko.com/en/coins/certik>`__
  - `Bounce Token (BOT) <https://www.coingecko.com/en/coins/bounce-token>`__

* :release:`1.8.2 <2020-10-27>`
* :bug:`1631` Fetching poloniex trades will now work properly again after they changed their trade date time format.
* :feature:`-` Support the following new MakerDAO vault collateral types: ``ETH-B``, ``USDT-A``, ``MANA-A``, ``PAXUSD-A``, ``COMP-A``, ``LRC-A``, ``LINK-A``.
* :feature:`1616` Support https://harvest.finance/ stablecoin vaults balance queries and claimable FARM token balance display.
* :feature:`1456` Take balances shown in DeFi overview into account in the total netvalue worth and in the dashboard and per account ethereum balances table.
* :feature:`1561` The application will now only log critical errors by default, allowing the user to change that on the log in screen.
* :feature:`1562` Add support for P2SH-P2WPKH and WPKH type of xPubs. User can now choose the xpub type when inputting from the UI.
* :bug:`1583` Users will not be taken to the reveal button when pressing tab in a form with a revealable input.
* :feature:`1122` Users can now import their metamask account addresses to rotki.
* :feature:`1458` Aave borrowing and liquidations are now also taken into account and displayed to the user. Also for historical aave queries a subgraph is used instead of blockchain event querying which makes the entire process considerably faster.
* :feature:`1194` Premium users can now manually backup or restore their databases.
* :bug:`1596` If the local DB of a premium user is both newer and bigger size than the remote, then do not ask the user whether to pull the remote DB or not.
* :feature:`1288` Users can now see the last premium database sync date in the save indicator when database sync is enabled.
* :bug:`1571` New user account with new premium keys will no longer fail to create an account the first time if premium keys are given at account creation time.
* :bug:`1559` Users can now properly refresh the blockchain balances in the Accounts & Balances page.
* :bug:`1564` Blockchain balances are now properly sorted by fiat currency value.
* :bug:`1558` Deleting an xPub that has no used derived addresses is now possible.
* :feature:`1560` Users can now see the total value of the accounts under an xpub.
* :feature:`-` Added support for the following tokens:

  - `Based Money ($BASED) <https://www.coingecko.com/en/coins/based-money>`__
  - `Filecoin (FIL) <https://www.coingecko.com/en/coins/filecoin>`__
  - `DefiPulse Index (DPI) <https://www.coingecko.com/en/coins/defipulse-index>`__
  - `renBTC (renBTC) <https://www.coingecko.com/en/coins/renbtc>`__
  - `Jarvis Reward Token (JRT) <https://www.coingecko.com/en/coins/jarvis-reward-token>`__
  - `Alpha Finance (ALPHA) <https://www.coingecko.com/en/coins/alpha-finance>`__
  - `Near Protocol (NEAR) <https://www.coingecko.com/en/coins/near>`__
  - `Venus (XVS) <https://www.coingecko.com/en/coins/venus>`__
  - `3x Short Cardano Token (ADABEAR) <https://www.coingecko.com/en/coins/3x-short-cardano-token>`__
  - `3x Long Cardano Token (ADABULL) <https://www.coingecko.com/en/coins/3x-long-cardano-token>`__
  - `DefiChain (DFI) <https://www.coingecko.com/en/coins/defichain>`__
  - `Ducato Protocol Token (DUCATO) <https://www.coingecko.com/en/coins/ducato-protocol-token>`__
  - `Consensus Cell Network (ECELL) <https://www.coingecko.com/en/coins/consensus-cell-network>`__
  - `Maro (MARO) <https://www.coingecko.com/en/coins/maro>`__
  - `Harvest Finance (FARM) <https://www.coingecko.com/en/coins/harvest-finance>`__
  - `PieDAO DOUGH v2 (DOUGH) <https://www.coingecko.com/en/coins/piedao-dough-v2>`__
  - `All Harvest finance stablecoin vault fAssets <https://github.com/harvest-finance/harvest#vaults>`__
  - `PickleToken (PICKLE) <https://www.coingecko.com/en/coins/pickle-finance>`__
  - `Curve.fi DAI/USDC/USDT Pool (3Crv) <https://etherscan.io/address/0x6c3f90f043a72fa612cbac8115ee7e52bde6e490>`__
  - `Curve.fi GUSD/3Crv (gusd3CRV) <https://etherscan.io/address/0xD2967f45c4f384DEEa880F807Be904762a3DeA07>`__
  - `Yearn Gemini USD vault (yGUSD) <https://etherscan.io/address/0xec0d8D3ED5477106c6D4ea27D90a60e594693C90>`__
  - `yearn Curve.fi DAI/USDC/USDT vault (y3Crv) <https://etherscan.io/address/0x9cA85572E6A3EbF24dEDd195623F188735A5179f>`__
  - `mStable USD (mUSD) <https://www.coingecko.com/en/coins/mstable-usd>`__
  - `Aave Interest bearing Aave Token (aAAVE) <https://etherscan.io/address/0xba3d9687cf50fe253cd2e1cfeede1d6787344ed5>`__
  - `Bidao (BID) <https://www.coingecko.com/en/coins/bidao>`__
  - `Audius (AUDIO) <https://www.coingecko.com/en/coins/audius>`__
  - `Easyfi (EASY) <https://www.coingecko.com/en/coins/easyfi>`__
  - `Binance leveraged token FILDOWN (FILDOWN) <https://www.cryptocompare.com/coins/fildown>`__
  - `Binance leveraged token FILUP (FILUP) <https://www.cryptocompare.com/coins/filup/>`__
  - `Binance leveraged token YFIDOWN (YFIDOWN) <https://www.cryptocompare.com/coins/yfidown>`__
  - `Binance leveraged token YFIUP (YFIUP) <https://www.cryptocompare.com/coins/yfiup/>`__
  - `Injective Token (INJ) <https://www.coingecko.com/en/coins/injective-protocol>`__
  - `Celo dollar (CUSD) <https://www.cryptocompare.com/coins/celousd/overview>`__
  - `Elastos (ELA) <https://www.coingecko.com/en/coins/elastos>`__
  - `KardiaChain Token (KAI) <https://www.coingecko.com/en/coins/kardiachain>`__

* :release:`1.8.1 <2020-10-05>`
* :feature:`1532` Users can now easily open links to external block explorers for their tracked blockchain addresses.
* :bug:`1530` Truncation of account addresses will now dynamically change based on the screen width.
* :feature:`224` Coingecko is now used for current price queries if cryptocompare fails. This will allow more tokens to be displayed.
* :feature:`1523` Trailing or leading whitespace in pasted addresses and api keys will now be properly removed.
* :feature:`1501` Assets that have been added to the ignore list will now be hidden from the dashboard.
* :bug:`1533` Premium Yearn vaults users should now be able to see a USD PNL per vault they used during the tax report.
* :bug:`1527` Premium Compound users should no longer get an exception during tax report.
* :feature:`808` Bitcoin xpubs are now supported. Given an xpub rotki derives all addresses locally and tracks those that have been used without compromising user privacy.

* :feature:`-` Added support for the following tokens:

  - `Compound Uni (cUNI) <https://www.coingecko.com/en/coins/compound-uniswap>`__
  - `YAMv3 (YAM) <https://www.coingecko.com/en/coins/yam>`__
  - `Avalanche (AVAX) <https://www.coingecko.com/en/coins/avalanche>`__
  - `BakeryToken (BAKE) <https://www.coingecko.com/en/coins/bakerytoken>`__
  - `Burger Swap (BURGER) <https://www.coingecko.com/en/coins/burger-swap>`__
  - `Pancake Swap (CAKE) <https://www.coingecko.com/en/coins/pancakeswap>`__
  - `Flamingo Finance (FLM) <https://www.coingecko.com/en/coins/flamingo-finance>`__
  - `Helium (HNT) <https://www.coingecko.com/en/coins/helium>`__
  - `New Bitshares (NBS) <https://www.coingecko.com/en/coins/new-bitshares>`__
  - `Sun Token (SUN) <https://www.coingecko.com/en/coins/sun-token>`__
  - `CBDao (BREE) <https://www.coingecko.com/en/coins/cbdao>`__
  - `Concentrated Voting Power (CVP) <https://www.coingecko.com/en/coins/powerpool-concentrated-voting-power>`__
  - `dHedge DAO Token (DHT) <https://www.coingecko.com/en/coins/dhedge-dao>`__
  - `Aavegotchi (GHST) <https://www.coingecko.com/en/coins/aavegotchi>`__
  - `Moji Experience Points (MEXP) <https://www.coingecko.com/en/coins/moji-experience-points>`__
  - `Polkastarter (POLS) <https://www.coingecko.com/en/coins/polkastarter>`__
  - `Rarible (RARI) <https://www.coingecko.com/en/coins/rarible>`__
  - `Rio DeFi (RFUEL) <https://www.coingecko.com/en/coins/rio-defi>`__
  - `Value Liquidity (VALUE) <https://www.coingecko.com/en/coins/value-liquidity>`__
  - `Beowulf (BWF) <https://www.coingecko.com/en/coins/beowulf>`__
  - `GSTCoin (GST) <https://www.coingecko.com/en/coins/gstcoin>`__
  - `Keep Token (KEEP) <https://www.coingecko.com/en/coins/keep-network>`__
  - `Aave Token (AAVE) <https://www.coingecko.com/en/coins/aave>`__

* :release:`1.8.0 <2020-09-23>`
* :feature:`1498` Users can now select the protocol(s) when resetting the DeFi history cache.
* :bug:`1504` Users can now properly start the application when the default backend port is used by another application.
* :feature:`1502` Add support for Binance lending assets.
* :feature:`1402` Yearn vaults historical data and total profit/loss per vault is now available. Also the ROI since inception is now visible next to each vault.
* :bug:`1491` All aave historical events should now be properly returned. Not only interest events.
* :bug:`1482` Use binance api server time to avoid clock skew error with the signatures
* :feature:`-` Users can now easily copy the address from the blockchain account view.
* :bug:`1453` Users will now see an validation error message when attempting to add an existing account.
* :feature:`804` Users can now track borrowing from Compound in the DeFi borrowing page.
* :feature:`597` Users can now track the interest earned by Compound loans in the DeFi lending page.
* :bug:`1462` ycrvRenWSBTC vault token should now properly appear in the dashboard and have its price calculated correctly.
* :bug:`1429` Pool together's plDAI and plUSDC are now correctly shown in the DeFi overview page.
* :bug:`1423` Fiat amounts in protocols details in the DeFi Overview are now correctly converted to the user's profit currency.
* :bug:`1430` Users can now delete manual balance entries where the label is an empty string.
* :feature:`1199` Users can now see the currency symbol next to the value for fiat currencies displayed in the UI.
* :feature:`1415` The navigation drawer has been re-ordered for better usability (the most-used pages have been floated up, and least-used moved to the bottom), and its icons have been updated to use Material Design Icons.
* :feature:`-` Added support for the following tokens:

  - `SushiToken (SUSHI) <https://www.coingecko.com/en/coins/sushi>`__
  - `Trustlines Network Token (TLN) <https://www.coingecko.com/en/coins/trustline-network>`__
  - `Uniswap (UNI) <https://www.coingecko.com/en/coins/uniswap>`__
  - `Crypto is Everywhere Around Me (CREAM) <https://www.coingecko.com/en/coins/cream>`__
  - `Bella Protocol (BEL) <https://www.coingecko.com/en/coins/bella-protocol>`__
  - `Elrond (EGLD) <https://www.coingecko.com/en/coins/elrond>`__
  - `Swerve DAO Token (SWRV) <https://www.coingecko.com/en/coins/swerve>`__
  - `Wing Finance (WING) <https://www.coingecko.com/en/coins/wing-finance>`__
  - `Akropolis Delphi (ADEL) <https://www.coingecko.com/en/coins/akropolis-delphi>`__
  - `AlphaLink (ANK) <https://www.coingecko.com/en/coins/alphalink>`__
  - `Corn (CORN) <https://www.coingecko.com/en/coins/corn>`__
  - `Salmon (SAL) <https://www.coingecko.com/en/coins/salmon>`__
  - `Carrot Finance (CRT) <https://www.coingecko.com/en/coins/carr-finance>`__
  - `FalconSwap Token (FSW) <https://www.coingecko.com/en/coins/falconswap>`__
  - `Unification (FUND) <https://www.coingecko.com/en/coins/unification>`__
  - `Hedget (HGET) <https://www.coingecko.com/en/coins/hedget>`__
  - `JackPool.Finance (JFI) <https://www.coingecko.com/en/coins/jackpool-finance>`__
  - `Pearl Finance (PEARL) <https://www.coingecko.com/en/coins/pearl-finance>`__
  - `tBridge Token (TAI) <https://www.coingecko.com/en/coins/tbridge-token>`__
  - `YF Link (YFL) <https://www.coingecko.com/en/coins/yf-link>`__
  - `YFValue (YFV) <https://www.coingecko.com/en/coins/yfvalue>`__
  - `Klaytn (KLAY) <https://www.coingecko.com/en/coins/klay>`__
  - `Klever (KLV) <https://www.coingecko.com/en/coins/klever>`__
  - `TerraKRW (KRT) <https://www.coingecko.com/en/coins/terra-krw>`__
  - `Latamcash (LMCH) <https://www.coingecko.com/en/coins/latamcash>`__
  - `Ravencoin Classic (RVC) <https://www.coingecko.com/en/coins/ravencoin-classic>`__
  - `Terra SDT (SDT) <https://www.coingecko.com/en/coins/terra-sdt>`__
  - `BiLira (TRYB) <https://www.coingecko.com/en/coins/bilira>`__
  - `Neutrino Dollar (USDN) <https://www.coingecko.com/en/coins/neutrino-dollar>`__
  - `Terra USD (UST) <https://www.cryptocompare.com/coins/ust/overview>`__
  - `Anyswap (ANY) <https://www.coingecko.com/en/coins/anyswap>`__
  - `Chi Gastoken (CHI) <https://www.coingecko.com/en/coins/chi-gastoken>`__
  - `Trump Wins Token (TRUMPWIN) <https://www.coingecko.com/en/coins/trump-wins-token>`__
  - `Trump Loses Token (TRUMPLOSE) <https://www.coingecko.com/en/coins/trump-loses-token>`__
  - `Binance leveraged token DOTDOWN (DOTDOWN) <https://www.cryptocompare.com/coins/dotdown>`__
  - `Binance leveraged token DOTUP (DOTUP) <https://www.cryptocompare.com/coins/dotup/>`__
  - `Binance leveraged token EOSDOWN (EOSDOWN) <https://www.cryptocompare.com/coins/eosdown>`__
  - `Binance leveraged token EOSUP (EOSUP) <https://www.cryptocompare.com/coins/eosup/>`__
  - `Binance leveraged token LTCDOWN (LTCDOWN) <https://www.cryptocompare.com/coins/ltcdown>`__
  - `Binance leveraged token LTCUP (LTCUP) <https://www.cryptocompare.com/coins/ltcup/>`__
  - `Binance leveraged token TRXDOWN (TRXDOWN) <https://www.cryptocompare.com/coins/trxdown>`__
  - `Binance leveraged token TRXUP (TRXUP) <https://www.cryptocompare.com/coins/trxup/>`__
  - `Binance leveraged token XRPDOWN (XRPDOWN) <https://www.cryptocompare.com/coins/xrpdown>`__
  - `Binance leveraged token XRPUP (XRPUP) <https://www.cryptocompare.com/coins/xrpup/>`__

* :release:`1.7.0 <2020-09-01>`
* :feature:`1092` Users can now refresh their manual balance entries.
* :feature:`1031` Users can now view their ethereum transactions in the history page.
* :feature:`1378` Support new OCEAN protocol token after token swap
* :feature:`1336` Balance of any of the user accounts in either yearn finance vaults or curve finance pools should now be auto-detected and displayed both in the dashboard and in the DeFi overview.
* :bug:`1393` When users set the "crypto to crypto trades" setting off, they will no longer see the USD equivalent part of crypto to crypto buys in the tax report history.
* :feature:`1085` Users can now view their exchange trades, along with there deposit and withdraw actions on the connected exchanges.
* :bug:`1321` CSV export formulas have now been fixed and should properly calculate profit/loss per different action type.
* :feature:`-` Add support for New Zealand Dollar (NZD) as a fiat currency
* :feature:`-` Add support for Brazilian Real (BRL) as a fiat currency
* :feature:`-` rotki users can now import data from their Crypto.com mobile application. For more information go to the data import component of rotki.
* :feature:`1361` Users of rotki will now no longer need to wait until the next version is available to be able to access the newly supported assets. rotki will pull newly available supported assets directly from Github.
* :bug:`1352` Defi cached state should now properly reset when an account is added or deleted.
* :bug:`1329` If aave historical data is queried in quick succession a UNIQUE constraint error will no longer be generated.
* :feature:`840` Add a new notification UI. Backend errors should now display a notification on the upper right corner.
* :feature:`983` The asset icons that are displayed in the rotki frontend have been revamped. We are now pulling icon data from coingecko so a lot more token/asset icons should be visible and up to date.
* :feature:`1235` Numerical displays can now be customized. Users can choose the thousands, the decimals separator. and the position of the currency symbol.
* :feature:`1186` Add tooltips to all app bar buttons (except drawer button)
* :bug:`1226` Fix "Get rotki Premium" menu button on macOS
* :feature:`-` Added support for the following tokens:

  - `YAM (YAM) <https://coinmarketcap.com/currencies/yam/>`__
  - `YAMv2 (YAMv2) <https://www.coingecko.com/en/coins/yam-v2>`__
  - `Serum (SRM) <https://coinmarketcap.com/currencies/serum/>`__
  - `Orion Protocol (ORN) <https://www.coingecko.com/en/coins/orion-protocol>`__
  - `Polkadot (DOT) <https://coinmarketcap.com/currencies/polkadot-new/>`__
  - `Curve DAO Token (CRV) <https://www.coingecko.com/en/coins/curve-dao-token>`__
  - `DIAToken (DIA) <https://coinmarketcap.com/currencies/dia-data/>`__
  - `Binance leveraged token BNBDOWN (BNBDOWN) <https://www.cryptocompare.com/coins/bnbdown/>`__
  - `Binance leveraged token BNBUP (BNBUP) <https://www.cryptocompare.com/coins/bnbup/>`__
  - `Binance leveraged token XTZDOWN (XTZDOWN) <https://www.cryptocompare.com/coins/xtzdown/>`__
  - `Binance leveraged token XTZUP (XTZUP) <https://www.cryptocompare.com/coins/xtzup/>`__
  - `Reserve Rights (RSR) <https://www.coingecko.com/en/coins/reserve-rights-token>`__
  - `The Sandbox (SAND) <https://www.coingecko.com/en/coins/sand>`__
  - `Tellor Tributes (TRB) <https://www.coingecko.com/en/coins/tellor>`__
  - `Nexus Mutual (NXM) <https://www.coingecko.com/en/coins/nxm>`__
  - `Wrapped Nexus Mutual (wNXM) <https://www.coingecko.com/en/coins/wrapped-nxm>`__
  - `Blocery Token (BLY) <https://www.coingecko.com/en/coins/blocery>`__
  - `DEXTools (DEXT) <https://www.coingecko.com/en/coins/dextools>`__
  - `DMM: Governance Token (DMG) <https://www.coingecko.com/en/coins/dmm-governance>`__
  - `DOS Network Token (DOS) <https://www.coingecko.com/en/coins/dos-network>`__
  - `Geeq (GEEQ) <https://www.coingecko.com/en/coins/geeq>`__
  - `MCDext Token (MCB) <https://www.coingecko.com/en/coins/mcdex>`__
  - `Mantra DAO (OM) <https://www.coingecko.com/en/coins/mantra-dao>`__
  - `PeerEx Network (PERX) <https://www.coingecko.com/en/coins/peerex-network>`__
  - `Parsiq Token (PRQ) <https://www.coingecko.com/en/coins/parsiq>`__
  - `Synthetic CBDAO (SBREE) <https://www.coingecko.com/en/coins/cbdao>`__
  - `Swingby (SWINGBY) <https://www.coingecko.com/en/coins/swingby>`__
  - `Cache Gold Token (CGT) <https://www.coingecko.com/en/coins/cache-gold>`__
  - `Centric (CNS) <https://www.coingecko.com/en/coins/centric>`__
  - `Sensorium (SENSO) <https://www.coingecko.com/en/coins/senso>`__
  - `Aave interest bearing YFI (aYFI) <https://etherscan.io/tx/0x259efe3b78bda8cf736a4afb30654d2e365cb42dc2cbe1fa8c64137673d848fd>`__
  - `Ampleforth (AMPL) <https://www.coingecko.com/en/coins/ampleforth>`__
  - `YFII.finance (YFII) <https://www.coingecko.com/en/coins/dfi-money>`__

* :release:`1.6.2 <2020-08-11>`
* :bug:`1311` When user logs out the app bar is no longer visible.
* :feature:`1303` User can now purge cached ethereum transactions and exchange data (deposits/withdrawals/trades). The next time data is fetched, the respective source will be queried to repopulate the local database cache. This might take some time depending on the amount of entries that will be queried.
* :feature:`1265` Removed fiat balance tracking as it was unnecessary. All fiat balances have now been migrated to manually tracked balances. Each fiat balance entry you had is now migrated to a corresponding manually tracked entry with location being "bank". As an example if you had 1500 EUR Fiat balance entry you will now have a manually tracked balance entry with 1500 EUR called "My EUR bank" and having a location bank.
* :bug:`1298` Fix an issue where it was not possible to add a new manual balances after editing one.
* :bug:`1243` Fix a problem where the "Get Premium" menu entry would not disappear without restarting the application.
* :feature:`1201` Changing the password when premium sync is enabled, will now display a warning to users about the change affecting synced instances.
* :feature:`1178` Users can now select which accounts they want to track for the activated defi modules. If none are selected all accounts are queried.
* :feature:`1084` Users can now select which of the available defi modules they want to activate.
* :bug:`1285` Properly track SNX tokens by pointing to the `migrated <https://blog.synthetix.io/proxy-contract-cutover-on-may-10/>`__ proxy contract
* :feature:`820` Multiple open ethereum nodes will be now also queried along with your own ethereum node or etherscan. But in smaller frequency so as not to spam those services. The additional nodes rotki now queries are:
  - MyCrypto
  - Blockscout
  - Avado pool
* :feature:`1213` Taxable actions table in the tax report and in the CSV exports now include a location.
* :bug:`1249` Fix some amounts not being converted to user's main currency correctly (two components were affected: Account Asset Balances in Accounts & Balances, and the AssetBalances component which was used in both Blockchain Balances as well as Exchange Balances sub-pages that showed totals across an asset).
* :bug:`1247` Fix glitchy autocomplete component usage which caused select menus to not open properly if the "dropdown arrows" were clicked. This has fixed the following select menus throughout the app: Asset Select, Tag Input and Tag Filter, Owned Tokens.
* :bug:`1234` Bittrex history can now be properly queried again. rotki uses bittrex v3 API from now and on.
* :bug:`-` ALQO historical price queries should now work properly again. Cryptocompare changed the mapping to XLQ and rotki had to adjust.
* :feature:`-` Added support for the following tokens

  - `UMA (UMA) <https://coinmarketcap.com/currencies/uma/>`__
  - `Ocean Protocol (OCEAN) <https://coinmarketcap.com/currencies/ocean-protocol/>`__
  - `Kusama (KSM) <https://coinmarketcap.com/currencies/kusama/>`__
  - `Pirl (PIRL) <https://coinmarketcap.com/currencies/pirl/>`__
  - `Synth sUSD (sUSD) <https://coinmarketcap.com/currencies/susd/>`__
  - `FIO Protocol (FIO) <https://coinmarketcap.com/currencies/fio-protocol/>`__
  - `THORChain (RUNE) <https://coinmarketcap.com/currencies/thorchain/>`__
  - `Suterusu (SUTER) <https://coinmarketcap.com/currencies/suterusu/>`__
  - `Darico Ecosystem Coin (DEC) <https://coinmarketcap.com/currencies/darcio-ecosystem-coin/>`__
  - `Decentr (DEC) <https://coinmarketcap.com/currencies/decentr/>`__
  - `Plutus DeFi (PLT) <https://coinmarketcap.com/currencies/plutusdefi/>`__
  - `Darwinia Network (RING) <https://coinmarketcap.com/currencies/darwinia-network/>`__
  - `TrustSwap (SWAP) <https://coinmarketcap.com/currencies/trustswap/>`__
  - `SUKU (SUKU) <https://coinmarketcap.com/currencies/suku/>`__
  - `Tendies (TEND) <https://coinmarketcap.com/currencies/tendies/>`__
  - `Unitrade (TRADE) <https://coinmarketcap.com/currencies/unitrade/>`__
  - `Augur v2 (REPV2) <https://www.augur.net/blog/v2-launch/>`__


* :release:`1.6.1 <2020-07-25>`
* :bug:`1202` The Linux rotki Appimage binary works properly again for Ubuntu <= 18.04. rotki v1.6.0 was not able to run in those Ubuntu versions.
* :bug:`1203` The selected tab in Accounts & Balances is now readable again.
* :bug:`1172` Fix the ethereum addresses for ``CHAI`` and ``cUSDT`` token.

* :release:`1.6.0 <2020-07-23>`
* :bug:`1072` Tax report progress report percentage should now work properly and negative numbers should no longer appear.
* :feature:`921` A new DeFi overview component is added. There the user can get an overview of all their balances across all DeFi protocols. For protocols that are supported further the user can click and be taken to the protocol specific page to see more details and historical accounting for that protocol.
* :feature:`1160` The Accounts & Balances page layout has been updated to increase usability. It is now split across three sub-pages: Blockchain Balances, Exchange Balances, Manual Balances (includes Fiat Balances). Exchange Balances is a new page where you will be able to see all of your asset balances for each connected exchange (previously this was only accessible from the Dashboard by clicking on an exchange).
* :bug:`1140` The Accounts column in "Blockchain Balances" is now correctly sorted by label (if it exists) or the account address.
* :bug:`1154` Tag filtering in "Manual Balances" within Accounts & Balances now works correctly if any balances do not have any tags assigned.
* :bug:`1155` Fix the cryptocompate price queries of LUNA Terra
* :bug:`1151` Fix for bittrex users so that if bittrex returns dates without a millisecond component rotki can still parse them properly.
* :feature:`1105` rotki now uses a standard compliant directory per OS to store user data. If the directory does not exist it is created and at the same time the old directory is migrated by copying it to the new one. The new directories per OS are:
  - Linux: ``~/.local/share/rotki/data``
  - OSX: ``~/Library/Application Support/rotki/data``
  - Windows: ``%LOCALAPPDATA%/rotki/data``
* :feature:`1004` Aave Lending is now supported. Users can see their deposited balance for lending, the borrowed balances and the respective APY/APR. Premium users can also retrieve all events history and get a total amount earned by lending per aToken.
* :feature:`530` You can now add ethereum addresses by ENS name. Simply use an ENS name in the ETH address field and if it can be resolved it will be appended to the tracked accounts.
* :bug:`1110` DSR Dai balance will now not be recounted with every force refresh querying of blockchain balances
* :feature:`-` Support TUSD, KNC, ZRX and the special USDC-B collateral types for makerdao vaults.
* :feature:`-` Support Australian Dollar (AUD) as fiat currency
* :feature:`-` Count Kraken `off-chain staked assets <https://support.kraken.com/hc/en-us/articles/360039879471-What-is-Asset-S-and-Asset-M->`__ as normal Kraken balance.

* :feature:`-` Added support for the following tokens

  - `Aave Interest bearing BAT (aBAT) <https://www.coingecko.com/en/coins/aave-bat>`__
  - `Aave Interest bearing Binance USD (aBUSD) <https://www.coingecko.com/en/coins/aave-busd>`__
  - `Aave Interest bearing ENJ (aENJ) <https://www.coingecko.com/en/coins/aave-enj>`__
  - `Aave Interest bearing ETH (aETH) <https://www.coingecko.com/en/coins/aave-eth>`__
  - `Aave Interest bearing KNC (aKNC) <https://www.coingecko.com/en/coins/aave-knc>`__
  - `Aave Interest bearing LEND (aLEND) <https://www.coingecko.com/en/coins/aave-lend>`__
  - `Aave Interest bearing LINK (aLINK) <https://www.coingecko.com/en/coins/aave-link>`__
  - `Aave Interest bearing MANA (aMANA) <https://www.coingecko.com/en/coins/aave-mana>`__
  - `Aave Interest bearing MKR (aMKR) <https://www.coingecko.com/en/coins/aave-mkr>`__
  - `Aave Interest bearing REN (aREN) <https://www.coingecko.com/en/coins/aave-ren>`__
  - `Aave Interest bearing REP (aREP) <https://www.coingecko.com/en/coins/aave-rep>`__
  - `Aave Interest bearing SNX (aSNX) <https://www.coingecko.com/en/coins/aave-snx>`__
  - `Aave Interest bearing SUSD (aSUSD) <https://www.coingecko.com/en/coins/aave-susd>`__
  - `Aave Interest bearing TUSD (aTUSD) <https://www.coingecko.com/en/coins/aave-tusd>`__
  - `Aave Interest bearing USDC (aUSDC) <https://www.coingecko.com/en/coins/aave-usdc>`__
  - `Aave Interest bearing USDT (aUSDT) <https://www.coingecko.com/en/coins/aave-usdt>`__
  - `Aave Interest bearing WBTC (aWBTC) <https://www.coingecko.com/en/coins/aave-wbtc>`__
  - `Aave Interest bearing ZRX (aZRX) <https://www.coingecko.com/en/coins/aave-zrx>`__
  - `Compound USDT (cUSDT) <https://www.coingecko.com/en/coins/compound-usdt>`__
  - `Compound SAI (cSAI) <https://www.coingecko.com/en/coins/compound-sai>`__
  - `Compound (COMP) <https://coinmarketcap.com/currencies/compound/>`__
  - `ALQO (ALQO) <https://coinmarketcap.com/currencies/alqo/>`__
  - `Solana (SOL) <https://coinmarketcap.com/currencies/solana/>`__
  - `Harmony (ONE) <https://coinmarketcap.com/currencies/harmony/>`__
  - `Binance leveraged token ADAUP (ADAUP) <https://www.cryptocompare.com/coins/adaup/overview>`__
  - `Binance leveraged token ADADOWN (ADADOWN) <https://www.cryptocompare.com/coins/adadown/overview>`__
  - `Binance leveraged token BTCUP (BTCUP) <https://www.cryptocompare.com/coins/btcup/overview>`__
  - `Binance leveraged token BTCDOWN (BTCDOWN) <https://www.cryptocompare.com/coins/btcdown/overview>`__
  - `Binance leveraged token ETHUP (ETHUP) <https://www.cryptocompare.com/coins/ethup/overview>`__
  - `Binance leveraged token ETHDOWN (ETHDOWN) <https://www.cryptocompare.com/coins/btcdown/overview>`__
  - `Binance leveraged token LINKUP (LINKUP) <https://www.cryptocompare.com/coins/linkup/overview>`__
  - `Binance leveraged token LINKDOWN (LINKDOWN) <https://www.cryptocompare.com/coins/linkdown/overview>`__
  - `Binance IDR Stable Coin (Binance IDR Stable Coin) <https://www.cryptocompare.com/coins/bidr/overview>`__
  - `Everipedia (IQ) <https://coinmarketcap.com/currencies/everipedia/>`__
  - `IQ.Cash (IQ) <https://coinmarketcap.com/currencies/iqcash/>`__
  - `pNetwork Token (PNT) <https://coinmarketcap.com/currencies/pnetwork/>`__
  - `Penta Network Token (PNT) <https://coinmarketcap.com/currencies/penta/>`__
  - `StormX (STMX) <https://coinmarketcap.com/currencies/stormx/>`__
  - `Arweave (AR) <https://coinmarketcap.com/currencies/arweave/>`__
  - `Celo (CELO) <https://coinmarketcap.com/currencies/celo/>`__
  - `Velas (VLX) <https://coinmarketcap.com/currencies/velas/>`__
  - `Kadena (KDA) <https://coinmarketcap.com/currencies/kadena/>`__
  - `All.me (ME) <https://www.cryptocompare.com/coins/me/overview>`__
  - `Dawn protocol (DAWN) <https://coinmarketcap.com/currencies/dawn-protocol/>`__
  - `Lucy (LUCY) <https://coinmarketcap.com/currencies/lucy/>`__
  - `BTEcoin (BTE) <https://www.coingecko.com/en/coins/btecoin>`__
  - `King DAG (KDAG) <https://coinmarketcap.com/currencies/king-dag/>`__
  - `The Force Protocol (FOR) <https://coinmarketcap.com/currencies/the-force-protocol/>`__
  - `Balancer (BAL) <https://coinmarketcap.com/currencies/balancer/>`__
  - `Bitchery (BCHC) <https://coinmarketcap.com/currencies/bitcherry/>`__
  - `bZx protocol (BZRX) <https://coinmarketcap.com/currencies/bzx-protocol/>`__
  - `Meta (MTA) <https://coinmarketcap.com/currencies/meta/>`__
  - `WazirX token (WRX) <https://coinmarketcap.com/currencies/wazirx/>`__
  - `xDAI STAKE (STAKE) <https://coinmarketcap.com/currencies/xdai/>`__
  - `yearn.finance (YFI) <https://coinmarketcap.com/currencies/yearn-finance/>`__
  - `MimbleWimbleCoin (MWC) <https://coinmarketcap.com/currencies/mimblewimblecoin/>`__

* :release:`1.5.0 <2020-06-10>`
* :bug:`986` Allows the unsetting of the RPC endpoint
* :feature:`918` Premium users can now set watchers for their vaults. When the watched vault gets below or above a certain collateralization ratio they get an email alert.
* :bug:`836` Allows the use of non-checksummed eth addresses in the frontend.
* :bug:`1016` rotki users can now delete their rotki premium API keys via API Keys -> rotki Premium.
* :feature:`1015` rotki now lets the user manually refresh and take a snapshot of their balances, even if the balance save frequency has not lapsed. This functionality is accessible through the Save Indicator (floppy disk icon on the app bar).
* :feature:`707` rotki now supports makerdao vaults. The vaults of the user are autodetected and they can see all details of each
  vault in the DeFi borrowing section. Premium users can also see historical information and total interest owed or USD lost to liquidation.
* :feature:`917` rotki now has a new and improved Dashboard. Users can view their total net worth as well as totals per source of balances (exchanges, blockchains, and manual entries), as well as filter the full asset listing.
* :bug:`995` Importing from cointracking.info should now work again. Adjust to the latest cointracking.info CSV export format.
* :feature:`971` rotki's initial loading and welcome screens are now integrated with an improved UI and a scrolling robin in the background to welcome the user.
* :feature:`988` General and Accounting settings have been consolidated into one Settings page, accessed via the User Menu, where users can access them as separate tabs.
* :feature:`763` rotki users can now change their password in the app's settings in the "User & Security" tab.
* :bug:`962` Fix infinite loop in Coinbase trades query
* :feature:`-` rotki users now have two options to further enhance their privacy. If a user wants to temporarily obscure values in the application, they can do so by turning `Privacy Mode` on and off in the User Menu. Additionally, if a user wants to scramble their data (e.g. before sharing screenshots or videos), they can do so via the `Scramble Data` setting in the application's General Settings.
* :bug:`966` rotki now supports the new Kraken LTC and XRP trade pairs
* :feature:`-` Added support for the following tokens

  - `Aave Interest bearing DAI (aDAI) <https://www.coingecko.com/en/coins/aave-dai>`__
  - `Loki (LOKI) <https://coinmarketcap.com/currencies/loki/>`__
  - `HyperDAO (HDAO) <https://coinmarketcap.com/currencies/hyperdao/>`__
  - `VeChain Thor (VTHO) <https://www.cryptocompare.com/coins/vtho/overview>`__
  - `JUST (JST) <https://coinmarketcap.com/currencies/just/>`__
  - `3x Short Bitcoin Cash Token (BCHBEAR) <https://coinmarketcap.com/currencies/3x-short-bitcoin-cash-token/>`__
  - `3x Long Bitcoin Cash Token (BCHBULL) <https://coinmarketcap.com/currencies/3x-long-bitcoin-cash-token/>`__
  - `3x Short Bitcoin SV Token (BSVBEAR) <https://coinmarketcap.com/currencies/3x-short-bitcoin-sv-token/>`__
  - `3x Long Bitcoin SV Token (BSVBULL) <https://coinmarketcap.com/currencies/3x-long-bitcoin-sv-token/>`__
  - `Connectome (CNTM) <https://www.coingecko.com/en/coins/connectome>`__
  - `Loon Network (LOON) <https://www.cryptocompare.com/coins/loon/overview>`__
  - `Celo Gold (CGLD) <https://coinmarketcap.com/currencies/celo/>`__
  - `TNC Coin (TNC) <https://coinmarketcap.com/currencies/tnc-coin/>`__
  - `Handshake (HNS) <https://coinmarketcap.com/currencies/handshake/>`__
  - `DEAPcoin (DEP) <https://coinmarketcap.com/currencies/deapcoin/>`__
  - `VideoCoin (VID) <https://coinmarketcap.com/currencies/videocoin/>`__
  - `Unicorn Technology International (UTI) <https://www.cryptocompare.com/coins/uti/overview>`__

* :release:`1.4.2 <2020-04-29>`
* :bug:`927` rotki should no longer fail to handle HTTP Rate limiting if your web3 providing node rate limits you.
* :bug:`950` If too many BTC accounts are used rotki will no longer delay for a long time due to balance query rate limiting. Proper batching of queries to both bitcoin.info and blockcypher is now happening.
* :bug:`942` Properly save all historical balances to the DB when a user has input manually tracked balances.
* :bug:`946` Handle the malformed response by kraken that is sent if a Kraken user has no balances.
* :bug:`943` If Kraken sends a malformed response rotki no longer raises a 500 Internal server error. Also if such an error is thrown during setup of any exchange and a stale object is left in the rotki state, trying to setup the exchange again should now work and no longer give an error that the exchange is already registered.
* :bug:`930` Etherscan API keys are now properly included in all etherscan api queries. Also etherscan API key is no longer compulsory.
* :feature:`922` Speed up ethereum chain balance queries by utilizing the eth-scan contract to batch multiple ether and token balance queries into a single call.
* :bug:`928` Action buttons in overlays ('Sign In', 'Create', etc.) are now never hidden by the privacy dialog regardless of resolution, app scaling, or zoom.
* :feature:`908` Adds the ability to view the full amount on tables when hovering over a hint (asterisk) indicating that the display number has been rounded.
* :bug:`924` LINK is now properly supported for Gemini balance and trade queries.
* :feature:`912` Adds total net value to the dashboard, fiat, and manual balances table. Makes account balance totals to reflect the filtered results.

* :feature:`-` Added support for the following tokens

  - `Cartesi token (CTSI) <https://coinmarketcap.com/currencies/cartesi/>`__
  - `Revain (REV) <https://coinmarketcap.com/currencies/revain/>`__
  - `Ubique chain of things (UCT) <https://coinmarketcap.com/currencies/ubique-chain-of-things/>`__
  - `YOU COIN (YOU) <https://coinmarketcap.com/currencies/you-coin/>`__

* :release:`1.4.1 <2020-04-22>`
* :bug:`-` Improve internal DSR mechanics so that even with hardly anyone using the DSR as of this release, rotki can still find DSR chi values to provide historical reports of DSR profit.
* :bug:`904` For Kraken users take into account the worst-case API call counter and make sure the maximum calls are not reached to avoid prolonged API bans.
* :bug:`895` Fixes manually tracked balances value column header not updating properly.
* :bug:`899` If a user's ethereum account held both old and new REP the new REP's account balance should now be properly automatically detected.
* :bug:`896` If the current price of an asset of a manually tracked balance can not be found, a value of zero is returned instead of breaking all manually tracked balances.
* :feature:`838` Added additional information about API Keys that can be set up by the user and grouped the API connections page into 3 categories: rotki Premium / Exchanges / External Services.
* :feature:`-` Added support for the following tokens

  - `Rupiah token (IDRT) <https://coinmarketcap.com/currencies/rupiah-token/>`__
  - `Exchange Union (XUC) <https://coinmarketcap.com/currencies/exchange-union/>`__
  - `Compound DAI (cDAI) <https://coinmarketcap.com/currencies/compound-dai/>`__
  - `Compound BAT (cBAT) <https://etherscan.io/address/0x6c8c6b02e7b2be14d4fa6022dfd6d75921d90e4e>`__
  - `Compound ETH (cETH) <https://etherscan.io/address/0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5>`__
  - `Compound Augur (cREP) <https://www.coingecko.com/en/coins/compound-augur>`__
  - `Compound USD coin (cUSDC) <https://www.coingecko.com/en/coins/compound-usd-coin>`__
  - `Compound Wrapped BTC (cWBTC) <https://www.coingecko.com/en/coins/compound-wrapped-btc>`__
  - `Compound 0x (cZRX) <https://www.coingecko.com/en/coins/compound-0x>`__

* :release:`1.4.0 <2020-04-16>`
* :feature:`807` Enables the addition and querying of manually tracked balances.
* :bug:`874` Fixed a bug where if invalid credentials were given to setup an exchange a 500 error was returned. The error is now handled gracefully.
* :bug:`852` PUT or DELETE on ``/api/1/blockchains/eth`` without etherscan keys configured no longer results in 500 internal server error.
* :feature:`869` The application menu now has some customized menu items. Users can now access the `Usage Guide`, `FAQ`, `Issues & Feature Requests`, and `Logs Directory` from within the Help menu. Additionally, there is a `Get rotki Premium` menu item for easy access to the premium subscription purchase page. Finally, both backend and frontend logs (``rotkehlchen.log`` and ``rotki-electron.log`` respectively) are now found in these standard locations per OS:

  * Linux: ``~/.config/rotki/logs``
  * OSX: ``~/Library/Application Support/rotki/logs``
  * Windows: ``<WindowsDrive>:\Users\<User>\Roaming\rotki\logs\``
* :feature:`862` Added a new API endpoint ``/api/1/ping`` as quick way to query API status for client/frontend initialization.
* :feature:`860` Added a new API endpoint ``/api/1/assets/all`` to query information about all supported assets.
* :bug:`848` Querying ``/api/1/balances/blockchains/btc`` with no BTC accounts tracked no longer results in a 500 Internal server error.
* :bug:`837` If connected to an ethereum node, the connection status indicator should now properly show that to the user.
* :bug:`830` If using alethio detecting tokens from an address that contains more than 10 tokens should now work properly
* :bug:`805` rotki can now accept passwords containing the " character
* :feature:`764` Gemini exchange is now supported. Trades, deposits, withdrawals and balances from that exchange can now be queried.
* :feature:`-` Add support for the South African Rand  (ZAR - R) as a fiat currency
* :feature:`-` Added support for the following tokens

  - `Standard Tokenization Protocol (STPT) <https://coinmarketcap.com/currencies/standard-tokenization-protocol/>`__
  - `IRISnet (IRIS) <https://coinmarketcap.com/currencies/irisnet/>`__
  - `Hive (HIVE) <https://coinmarketcap.com/currencies/hive-blockchain/>`__
  - `Hive dollar (HBD) <https://coinmarketcap.com/currencies/hive-dollar/>`__
  - `Swipe (SXP) <https://coinmarketcap.com/currencies/swipe/>`__
  - `Elamachain (ELAMA) <https://coinmarketcap.com/currencies/elamachain/>`__
  - `Starchain (STC) <https://coinmarketcap.com/currencies/starchain/>`__
  - `3X Short Bitcoin Token (BEAR) <https://coinmarketcap.com/currencies/3x-short-bitcoin-token/>`__
  - `3X Long Bitcoin Token (BULL) <https://coinmarketcap.com/currencies/3x-long-bitcoin-token/>`__
  - `3X Short Ethereum Token (ETHBEAR) <https://coinmarketcap.com/currencies/3x-short-ethereum-token/>`__
  - `3X Long Ethereum Token (ETHBULL) <https://coinmarketcap.com/currencies/3x-long-ethereum-token/>`__
  - `3X Short TRX Token (TRXBEAR) <https://coinmarketcap.com/currencies/3x-short-trx-token/>`__
  - `3X Long TRX Token (TRXBULL) <https://coinmarketcap.com/currencies/3x-long-trx-token/>`__
  - `3X Short EOS Token (EOSBEAR) <https://www.cryptocompare.com/coins/eosbear/overview>`__
  - `3X Long EOS Token (EOSBULL) <https://www.cryptocompare.com/coins/eosbull/overview>`__
  - `3X Short XRP Token (XRPBEAR) <https://www.cryptocompare.com/coins/xrpbear/overview>`__
  - `3X Long XRP Token (XRPBULL) <https://www.cryptocompare.com/coins/xrpbull/overview>`__
  - `3X Short BNB Token (BNBBEAR) <https://coinmarketcap.com/currencies/3x-short-bnb-token/>`__
  - `3X Long BNB Token (BNBBULL) <https://coinmarketcap.com/currencies/3x-long-bnb-token/>`__
  - `HEX (HEX) <https://www.coingecko.com/en/coins/hex>`__
  - `Binance KRW (BKRW) <https://www.cryptocompare.com/coins/bkrw/overview>`__


* :release:`1.3.0 <2020-03-20>`
* :feature:`779` OSX: User can now exit the application by simply pressing [X]
* :bug:`794` If etherscan rate limits the user it should now be handled correctly after their new changes ... again
* :feature:`643` rotki will now autodetect the tokens owned by each of your ethereum accounts. Integration with alethio is possible, and you can add an Alethio API key.
* :bug:`790` SegWit addresses (Bech32) can now be added to BTC balances.
* :feature:`-` rotki should now remember your window size, position, and maximized state after closing the app.
* :bug:`783` Fixes the update indicator to indicate to users if their client is out of date.
* :feature:`-` Added support for the following tokens

  - `Bosagora (BOA) <https://coinmarketcap.com/currencies/bosagora/>`__
  - `Nervos Network (CKB) <https://coinmarketcap.com/currencies/nervos-network/>`__
  - `Molecular Future Token (MOF) <https://coinmarketcap.com/currencies/molecular-future/>`__
* :feature:`-` Add support for the newly added kraken FX trade pairs

* :release:`1.2.1 <2020-03-10>`
* :bug:`770` Adds loading screen while waiting for the backend to start.
* :bug:`772` Getting a rate limit error from Etherscan should be now handled properly.
* :feature:`-` Support TRX in kraken, since it got listed.

* :release:`1.2.0 <2020-03-01>`
* :feature:`705` Support MakerDAO's DAI Savings Rate (DSR)
* :bug:`502` The OSX rotki app icon should no longer be blurry.
* :bug:`698` rotki should now also display the version in the UI for Windows and OSX.
* :bug:`709` rotki no longer crashes after second time of opening the application in Windows.
* :bug:`716` The rotki logs for linux now go into a proper directory: ``~/.config/rotki/logs``
* :feature:`461` You can now label your blockchain accounts and tag them with any number of custom tags to group them into categories. Tags can be customized.
* :bug:`739` If there is an error during DBUpgrade or if the user uses old software to run a new DB we don't crash and burn with a 500 error but instead show a proper message.
* :bug:`731` Fixed cointracking file import.
* :bug:`726` Fail gracefully and don't throw a 500 server error if blockchain balance query fails.
* :bug:`724` If latest block remote query fails do not revert to etherscan but persist with using the provided ethereum node after warning the user.
* :feature:`-` Added support for the following tokens

  - `LTO Network (LTO) <https://coinmarketcap.com/currencies/lto-network/>`__
  - `Verasity (VRA) <https://coinmarketcap.com/currencies/verasity/>`__
  - `Chai (CHAI) <https://etherscan.io/token/0x06af07097c9eeb7fd685c692751d5c66db49c215/>`__
  - `Coti (COTI) <https://coinmarketcap.com/currencies/coti/>`__
  - `MovieBloc (MBL) <https://coinmarketcap.com/currencies/moviebloc/>`__
  - `Alibaba Coin (ABBC) <https://coinmarketcap.com/currencies/abbc-coin/>`__
  - `WaykiChain (WICC) <https://coinmarketcap.com/currencies/waykichain/>`__

* :release:`1.1.1 <2020-02-06>`
* :bug:`693` Fix crash in OSX .dmg package version that occurred with v1.1.0

* :release:`1.1.0 <2020-02-05>`
* :feature:`626` rotki now accepts addition of API keys for external services such as etherscan or cryptocompare.
* :feature:`46` Coinbase Pro is now supported. Trades, deposits, withdrawals and balances in that exchange can now be queried.
* :feature:`583` The UI's notifications can finally be copy pasted.
* :feature:`168` Users can now force-refresh exchange/blockchain balances via the UI and ignore the cache.
* :feature:`354` Introduces a modern, easily extendable material design UI based on Vue.js and Vuetify.
* :feature:`404` Removed ZMQ as the messaging layer between backend - frontend and introduced a full-fledged REST API instead.
* :bug:`465` Asset icons and names show consistently in the UI after the vue.js rewrite.
* :feature:`-` Added support for the following tokens

  - `Orchid (OXT) <https://coinmarketcap.com/currencies/orchid/>`__
  - `DREP (DREP) <https://coinmarketcap.com/currencies/drep/>`__
  - `Origin Protocol (OGN) <https://coinmarketcap.com/currencies/origin-protocol/>`__
  - `Token Club (TCT) <https://coinmarketcap.com/currencies/tokenclub/>`__
  - `Tap (XTP) <https://coinmarketcap.com/currencies/tap/>`__
  - `Xensor (XSR) <https://coinmarketcap.com/currencies/xensor/>`__

* :release:`1.0.7 <2020-01-04>`
* :bug:`605` Adding a premium API key via the front-end now works properly again.
* :bug:`602` Fixed a bug that lead to the coinbase exchange integration not working.

* :release:`1.0.6 <2019-12-31>`
* :bug:`589` If there is an error an unexpected error during sign-in properly catch it and add a log entry.
* :bug:`588` The electron log is now written in the proper directory depending on the Operating system.
* :bug:`587` If a user has a disabled taxfree period setting rotki no longer fails to sign the user in.
* :bug:`561` Export unique asset symbols during CSV exporting and not long name descriptions.
* :feature:`-` Add support for the Turkish Lyra  (TRY - ₺) as a fiat currency
* :feature:`-` Add support for the Russian ruble (RUB - ‎₽) as a fiat currency
* :feature:`-` Add support for the Swiss Franc (CHF - Fr.) as a fiat currency
* :feature:`-` Added support for the following tokens

  - `Troy (TROY) <https://coinmarketcap.com/currencies/troy/>`__
  - `Hycon (HYC) <https://coinmarketcap.com/currencies/hycon/>`__

* :release:`1.0.5 <2019-11-30>`
* :feature:`547` Support Multicollateral DAI upgrade and Single Collateral DAI renaming to SAI.
* :bug:`545` Trades from all Kraken pairs should now be processed properly again. For example all SC trade pairs should now work again.
* :bug:`543` User will not get unexpected balance results in the same rotki run due to same cache being used for different arguments.
* :feature:`541` If the user allows anonymous usage analytics are submitted to a server for analysis of the application's active users.
* :feature:`-` Rebranding Rotkehlchen to rotki inside the application. All website and api links should now target rotki.com
* :bug:`534` Old external trades can now be edited/deleted properly again.
* :bug:`527` If cryptocompare query returns an empty object rotki client no longer crashes.

* :feature:`-` Added support for the following tokens

  - `ArpaChain (ARPA) <https://coinmarketcap.com/currencies/arpa-chain/>`__
  - `Kava (KAVA) <https://coinmarketcap.com/currencies/kava/>`__
  - `Medibloc (MED) <https://coinmarketcap.com/currencies/medibloc/>`__
  - `FNB Protocol (FNB) <https://coinmarketcap.com/currencies/fnb-protocol/>`__
  - `Pledge coin (PLG) <https://coinmarketcap.com/currencies/pledge-coin/>`__
  - `SIX Network (SIX) <https://coinmarketcap.com/currencies/six/>`__
  - `W Green Pay (WGP) <https://coinmarketcap.com/currencies/w-green-pay/>`__
  - `FLETA (FLETA) <https://coinmarketcap.com/currencies/fleta/>`__
  - `PAX Gold (PAXG) <https://coinmarketcap.com/currencies/pax-gold/>`__
  - `Hdac (HDAC) <https://coinmarketcap.com/currencies/hdac/>`__

* :release:`1.0.4 <2019-10-04>`
* :feature:`498` Users can now import data from Cointracking into rotki. Create a CSV export from Cointracking and import it from the Import Data menu.
* :bug:`500` Fix cryptocompare price queries for LBRY credits.
* :feature:`505` Support the new cryptocompare v2 historical price [API](https://blog.cryptocompare.com/historical-data-api-update-4ee44c549a8f).
* :feature:`499` All actions (trades, deposits, withdrawals, ethereum transactions, margin positions) are now saved in the DB.
* :feature:`-` Support WorldWideAssetExchange token for Bittrex after it got renamed to `WAXP <https://international.bittrex.com/Market/Index?MarketName=BTC-WAXP>`__ in that exchange.
* :feature:`-` Added support for the following tokens

  - `Perling (PERL) <https://coinmarketcap.com/currencies/perlin/>`__
  - `HedgeTrade (HEDG) <https://coinmarketcap.com/currencies/hedgetrade/>`__
  - `Hedera Hashgraph (HBAR) <https://coinmarketcap.com/currencies/hedera-hashgraph/>`__
  - `Morpheus Network (MRPH) <https://coinmarketcap.com/currencies/morpheus-network/>`__
  - `Chiliz (CHZ) <https://coinmarketcap.com/currencies/chiliz/>`__
  - `Binance USD (BUSD) <https://coinmarketcap.com/currencies/binance-usd/>`__
  - `Band Protocol (BAND) <https://coinmarketcap.com/currencies/band-protocol/>`__
  - `Beam Token (BEAM) <https://coinmarketcap.com/currencies/beam/>`__

* :release:`1.0.3 <2019-08-30>`
* :feature:`453` If a newer version exists the user is notified at the start of the application and is given a link to download it.
* :feature:`487` USDT can now also be monitored as an ethereum token.
* :feature:`26` rotki is now available as a .dmg installer for OSX.
* :bug:`426` Opening the rotki electron app in OSX now works properly the first time.
* :feature:`296` Add support for the Coinbase exchange.
* :bug:`480` Calculating accounting with empty history no longer throws an exception.
* :bug:`469` Fixes error with OTC trades.
* :bug:`463` Converts tax report start and end time to local time.
* :bug:`467` Removing ETH tokens for which a cryptocompare query failed to find a price now work properly.
* :feature:`458` Binance users now also have their deposit/withdrawal history taken into account during profit/loss calculation.
* :feature:`457` Bittrex users now also have their deposit/withdrawal history taken into account during profit/loss calculation.
* :bug:`451` An assertion will no longer stop balances from being saved for some FIAT assets.

* :feature:`-` Added support for the following tokens

  - `Pixel <https://coinmarketcap.com/currencies/pixel/>`__
  - `Bittrex Credit Tokens <https://bittrex.zendesk.com/hc/en-us/articles/360032214811/>`__
  - `Cocos-BCX <https://coinmarketcap.com/currencies/cocos-bcx/>`__
  - `Akropolis <https://coinmarketcap.com/currencies/akropolis/>`__

* :release:`1.0.2 <2019-08-04>`
* :feature:`-` Added support for the following tokens

  - `Contentos <https://coinmarketcap.com/currencies/contentos/>`__
* :feature:`442` If a user provides a Kraken API key with insufficient permissions we no longer accept it and also provide them with a proper error message.
* :bug:`443` Fix bug in deserialization of non-exact floating point kraken timestamp values which could lead to a crash during tax report generation.

* :release:`1.0.1 <2019-08-02>`
* :feature:`425` Users can now provide arguments to the backend via a config file. For more information check the `docs <https://rotkehlchen.readthedocs.io/en/latest/usage_guide.html#set-the-backend-s-arguments>`__.
* :feature:`-` Added support for the following tokens

  - `Luna Coin <https://coinmarketcap.com/currencies/luna-coin/>`__
  - `Luna Terra <https://coinmarketcap.com/currencies/terra/>`__
  - `Spin Protocol <https://coinmarketcap.com/currencies/spin-protocol/>`__
  - `Blockcloud <https://coinmarketcap.com/currencies/blockcloud/>`__
  - `Bloc.Money <https://coinmarketcap.com/currencies/bloc-money/>`__
  - `Chromia  <https://coinmarketcap.com/currencies/chromia/>`__
* :feature:`428` Better handle unexpected data from external sources.
* :bug:`76` Handle poloniex queries returning null for the fee field.
* :bug:`432` If historical price for a trade is not found gracefully skip the trade. Also handle cryptocompare query edge case.
* :bug:`429` Properly handle 429 http response from blockchain.info by backing off by the suggested number of seconds and then trying again.

* :release:`1.0.0 <2019-07-22>`
* :bug:`420` There are no more negative percentages at tax report generation progress
* :bug:`392` Revisiting usersettings properly updates per account tables if an account has been deleted before.
* :bug:`325` Tracking accounts/tokens in user settings will now be immediately reflected on the dashboard.
* :bug:`368` Fixes broken navigation after visiting Statistics page.
* :bug:`361` Rotkehlchen no longer misses the last trade when processing history inside a timerange.
* :bug:`349` Copy paste should now work on OSX.
* :feature:`332` Add notifications area for actionable warnings/errors.
* :feature:`350` Add support for remote ethereum nodes and not just local ones.
* :feature:`329` Maintain a list of supported assets and converters from/to each exchange or service.
* :feature:`194` Add setting for date display format.
* :bug:`334` Handle too many requests error for the exchangerates api.
* :bug:`323` Properly display usd value For JPY and some other assets in kraken where XXBT is the quote asset.
* :bug:`320` The user settings pane is now always responsive, even when loaded a second time.
* :feature:`313` Premium feature: The statistic pane now has two different graphs to explore the distribution of value of the user. One shows the distribution of the total net value across different locations and the other across all assets the user holds.
* :feature:`312` Premium feature: The statistic pane now has a graph where users can check how any asset's amount and total usd value progresses over time.
* :bug:`314` Exchangerates api is now queried with priority and as such there are no more delays at the startup of the application due to unresponsive FOREX api calls.
* :feature:`272` Added a statistics pane. Premium users can now see a graph of their net value over time there.
* :bug:`299` IOTA historical price queries now work properly.
* :bug:`288` After a user re-login querying fiat prices will no longer throw exceptions.
* :bug:`273` Fallback to fetching NANO Price using XRB (Raiblocks) symbol before the rebranding.
* :bug:`283` OTC Trades table is now properly rendered again
* :feature:`268` Version name is now included in rotkehlchen binaries and other artifacts.

* :release:`0.6.0 <2019-01-21>`
* :feature:`92` Cache and have multiple APIs to query for fiat price queries.
* :feature:`222` Add a progress indicator during the tax report generation.
* :bug:`134` When rotkehlchen makes too many requests to Binance and gets a 429 response it now backs off and waits a bit.
* :bug:`241` When incurring margin trade loss the lost asset's available amount is now also reduced.
* :bug:`240` Poloniex settlement buys now incur the correct amount of BTC loss when processed.
* :bug:`218` Tax report details in the UI should no longer show NaN values in some columns.
* :bug:`231` Selling an asset that will fork, before it does now also reduces the forked asset amount.
* :bug:`232` Multiple rotkehlchen users will no longer share same cache files.
* :feature:`229` Rotkehlchen can now work and migrate to sqlcipher v4.
* :bug:`206` Fixes an error when adding a bitcoin account for the first time.
* :bug:`209` Fixes error during login due to invalid date being saved.
* :bug:`223` Fix error in profit/loss calculation due to bugs in the search of the FIFO queue of buy events.
* :feature:`221` Rotkehlchen is now shielded against inconsistencies of cryptocompare FIAT data.
* :bug:`219` Poloniex BTC settlement loss calculation is now correct.
* :bug:`217` Tax report CSV exports should now agree with the app report.
* :bug:`211` Handle the BCHSV fork in Kraken properly.

* :release:`0.5.0 <2018-11-10>`
* :bug:`201` Having ICN in Kraken from 31/10 to 31/11 2018 will not lead rotkehlchen to crash.
* :feature:`186` Pressing Enter at signin/create new account and other popups will submit them just like clicking the form button.
* :bug:`197` Rotkehlchen no longer crashes at restart if a "No" tax_free_period is given
* :bug:`185` Ethereum node connection indicator should always properly indicate the connection status to the underlying ethereum node
* :bug:`184` If Rotkehlchen brand name in top left is clicked, open browser to rotkehlchen.io instead of showing the sign-in popup
* :bug:`187` Exchange balance tables no longer become unresponsive if visited multiple times.
* :feature:`178` New logout api call. Users can now logout of a rotkehlchen session.
* :bug:`181` Take 0 net balance into account when doing balance queries and not crash.
* :bug:`156` Overflow should now scroll completely and properly on mac.
* :feature:`138` Add an option to allow for anonymizing of all sensitive rotkehlchen logs.
* :feature:`132` Added a UI widget showing if rotkehlchen is connected to an ethereum node
* :bug:`173` Price querying for IOTA should now work properly with cryptocompare

* :release:`0.4.0 <2018-09-23>`
* :feature:`144` Rotkehlchen now starts fully supporting Bitmex and allows querying Bitmex history for tax calculations.
* :bug:`163` Properly handle errors in the tax report calculation and in other asynchronous tasks.
* :bug:`155` Check if the local ethereum node is synced before querying balances from it.
* :feature:`153` Add a ``version`` command to display the rotkehlchen version.
* :bug:`159` Gracefully exit if an invalid argument is provided.
* :bug:`151` If an asset stored at Bittrex does not have a BTC market rotkehlchen no longer crashes.
* :feature:`148` Add icons for all tokens to the UI.
* :feature:`74` Add experimental support for Bitmex. Supporting only simple balance query for now.
* :bug:`135` Fix bug in converting binance sell trades to the common rotkehlchen format
* :bug:`140` Don't log an error if the manual margin file is not found

* :release:`0.3.2 <2018-08-25>`
* :feature:`95` Add a UI widget to display the last time the balance data was saved in the DB.
* :bug:`126` Refuse to generate a new tax report if one is in progress and also clean previous report before generating a new one.
* :bug:`123` Return USD as default main currency if DB is new
* :bug:`101` Catch the web3 exception if using a local client with an out of sync chain and report a proper error in the UI
* :bug:`86` Fixed race condition at startup that could result in the banks balance displaying as NaN.
* :bug:`103` After removing an exchange's API key the new api key/secret input form is now properly re-enabled
* :bug:`99` Show proper error if kraken or binance api key validation fails due to an invalid key having been provided.

* :release:`0.3.1 <2018-06-25>`
* :bug:`96` Periodic balance data storage should now also work from the UI.

* :release:`0.3.0 <2018-06-24>`
* :feature:`90` Add configuration option for it and periodically save balances data in the database
* :bug:`91` Provide more accurate name for the setting for the date from which historical data starts
* :bug:`89` Many typing bugs were found and fixed
* :bug:`83` Fix a bug that did not allow adding or removing ethereum tokens from the tracker
* :feature:`79` Do not crash with exception if an exchange is unresponsive, but instead warn the user.
* :bug:`77` Fix bug caused by reading `taxfree_after_period` from the database

* :release:`0.2.2 <2018-06-05>`
* :bug:`73` Fixer.io api switched to be subscription based and its endpoints are now locked, so we switch to a different currency converter api.
* :bug:`68` All kraken pairs should now work properly. Users who hold XRP, ZEC, USD, GP, CAD, JPY, DASH, EOSD and USDT in kraken will no longer have any problems.

* :release:`0.2.1 <2018-05-26>`
* :bug:`66` Persist all eth accounts in the database as checksummed. Upgrade all existing DB accounts.
* :bug:`63` Unlocking a user account for an application is no longer slow if you have lots of historical price cache files.
* :bug:`61` Overcome etherscan's limit of 20 accounts per query by splitting the accounts list

* :release:`0.2.0 <2018-05-13>`
* :feature:`51` Add customization for the period of time after which trades are tax free.
* :bug:`50` rotkehlchen --help now works again
* :feature:`45` Add option to customize including crypto to crypto trades.
* :feature:`42` Move the accounting settings to their own page.

* :release:`0.1.1 <2018-04-27>`
* :bug:`37` Fix a bug where adding an ethereum account was throwing an exception in the UI.

* :release:`0.1.0 <2018-04-23>`
