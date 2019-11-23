MCDAI_LAUNCH_TS = 1574035200

# https://blog.kraken.com/post/3061/kraken-is-supporting-dais-multi-collateral-upgrade/
# November 18th, 14:00 UTC
# For Kraken any DAI trade before this date is SAI and after it, should be MCDAI (DAI)
KRAKEN_DAI_UPGRADE_TS = 1574085600

# https://support.coinbase.com/customer/portal/articles/2982947
# Between November 18 and December 2 any MCDAI sent to Coinbase will be stored in temporary
# MCDAI wallet. Any DAI sent after November 18 will be shown as DAI. On December 2nd all Single
# collateral DAI will be turned to Multicollateral and DAI will mean the multicollateral
# counterpart MCDAI will cease to exist. After December 2nd any single collateral DAI
# sent to coinbase will be shown as SAI. SAI support may be dropped from Coinbase at any time.
COINBASE_DAI_UPGRADE_TS = MCDAI_LAUNCH_TS

# https://bittrex.zendesk.com/hc/en-us/articles/360035866431-Support-for-the-Dai-DAI-Multi-Collateral-Dai-Upgrade
# After November 18 DAI is renamed to SAI and both pairs exist in the exchange.
BITTREX_DAI_UPGRADE_TS = MCDAI_LAUNCH_TS
