#!/usr/bin/env python3
"""Find missing endpoints in FastAPI migration"""

import ast
import re
from pathlib import Path
from collections import defaultdict

# Manual mapping of Flask resources to expected FastAPI modules
RESOURCE_MAPPING = {
    # Base
    'PingResource': 'async_base.py',
    'InfoResource': 'async_base.py', 
    'SettingsResource': 'async_base.py',
    'AsyncTasksResource': 'async_base.py',
    
    # Assets
    'AllAssetsResource': 'async_assets_extended.py',
    'AssetsMappingResource': 'async_assets_extended.py',
    'AssetsSearchResource': 'async_assets_extended.py',
    'AssetsSearchLevenshteinResource': 'async_assets_extended.py',
    'AssetsTypesResource': 'async_assets_extended.py',
    'AssetsReplaceResource': 'async_assets_extended.py',
    'AssetUpdatesResource': 'async_assets_extended.py',
    'AssetIconsResource': 'async_assets.py',
    'IgnoredAssetsResource': 'async_assets_extended.py',
    'OwnedAssetsResource': 'async_assets_extended.py',
    'UserAssetsResource': 'async_assets_extended.py',
    'CustomAssetsResource': 'async_assets.py',
    'CustomAssetsTypesResource': 'async_assets.py',
    'CounterpartyAssetMappingsResource': 'async_assets_extended.py',
    'LocationAssetMappingsResource': 'async_assets_extended.py',
    'LatestAssetsPriceResource': 'async_assets.py',
    'AllLatestAssetsPriceResource': 'async_assets.py',
    'HistoricalAssetsPriceResource': 'async_assets.py',
    'HistoricalAssetAmountsResource': 'async_statistics.py',
    'HistoricalPricesPerAssetResource': 'async_statistics.py',
    
    # Balances
    'AllBalancesResource': 'async_balances.py',
    'BlockchainBalancesResource': 'async_balances.py',
    'ExchangeBalancesResource': 'async_balances.py',
    'ManuallyTrackedBalancesResource': 'async_balances.py',
    
    # Blockchain
    'BlockchainTransactionsResource': 'async_blockchain.py',
    'EvmTransactionsResource': 'async_blockchain.py',
    'EvmlikeTransactionsResource': 'async_blockchain.py',
    'EvmPendingTransactionsDecodingResource': 'async_blockchain.py',
    'EvmlikePendingTransactionsDecodingResource': 'async_blockchain.py',
    'EthereumAirdropsResource': 'async_blockchain.py',
    'ExternalServicesResource': 'async_blockchain.py',
    'BlockchainsAccountsResource': 'async_blockchain.py',
    'EvmAccountsResource': 'async_blockchain.py',
    'EvmTransactionsHashResource': 'async_blockchain.py',
    'RefetchEvmTransactionsResource': 'async_blockchain.py',
    
    # NFT
    'NFTSResource': 'async_nfts.py',
    'NFTSBalanceResource': 'async_nfts.py',
    'NFTSPricesResource': 'async_nfts.py',
    
    # ETH2
    'Eth2ValidatorsResource': 'async_eth2.py',
    'Eth2StakePerformanceResource': 'async_eth2.py',
    'Eth2DailyStatsResource': 'async_eth2.py',
    'Eth2StakingEventsResource': 'async_eth2.py',
    
    # DeFi
    'LiquityTrovesResource': 'async_defi.py',
    'LiquityStakingResource': 'async_defi.py',
    'LiquityStabilityPoolResource': 'async_defi.py',
    'LoopringBalancesResource': 'async_defi.py',
    'PickleDillResource': 'async_defi.py',
    'ModuleStatsResource': 'async_defi.py',
    'EvmModuleBalancesResource': 'async_defi.py',
    'EvmModuleBalancesWithVersionResource': 'async_defi.py',
    'DefiMetadataResource': 'async_defi.py',
    
    # Exchanges
    'ExchangesResource': 'async_exchanges.py',
    'ExchangesDataResource': 'async_exchanges.py',
    'ExchangeRatesResource': 'async_exchanges.py',
    
    # Database
    'DatabaseInfoResource': 'async_database.py',
    'DatabaseBackupsResource': 'async_database.py',
    'TagsResource': 'async_database.py',
    'DBSnapshotsResource': 'async_database.py',
    
    # History
    'HistoryProcessingResource': 'async_history.py',
    'HistoryStatusResource': 'async_history.py',
    'HistoryExportingResource': 'async_history.py',
    'HistoryDownloadingResource': 'async_history.py',
    'HistoryEventResource': 'async_history.py',
    'HistoryActionableItemsResource': 'async_history.py',
    'ExportHistoryEventResource': 'async_history.py',
    'ExportHistoryDownloadResource': 'async_history.py',
    
    # Accounting
    'AccountingReportsResource': 'async_accounting.py',
    'AccountingReportDataResource': 'async_accounting.py',
    'AccountingRulesResource': 'async_accounting.py',
    'AccountingRulesImportResource': 'async_accounting.py',
    'AccountingRulesExportResource': 'async_accounting.py',
    
    # Users
    'UsersResource': 'async_users.py',
    'UsersByNameResource': 'async_users.py',
    'UserPasswordChangeResource': 'async_users.py',
    'UserPremiumKeyResource': 'async_users.py',
    'UserPremiumSyncResource': 'async_users.py',
    'UserNotesResource': 'async_users.py',
    
    # Utils
    'RpcNodesResource': 'async_utils.py',
    'OraclesResource': 'async_utils.py',
    'NamedOracleCacheResource': 'async_utils.py',
    'MessagesResource': 'async_utils.py',
    'EvmCounterpartiesResource': 'async_utils.py',
    'EvmProductsResource': 'async_utils.py',
    'LocationResource': 'async_utils.py',
    'TypesMappingsResource': 'async_utils.py',
    'ClearCacheResource': 'async_utils.py',
    'ProtocolDataRefreshResource': 'async_utils.py',
    
    # Statistics
    'StatisticsNetvalueResource': 'async_statistics.py',
    'StatisticsAssetBalanceResource': 'async_statistics.py',
    'StatisticsValueDistributionResource': 'async_statistics.py',
    'StatisticsRendererResource': 'async_statistics.py',
    'StatsWrapResource': 'async_statistics.py',
}

def get_flask_resources_detailed(resources_file):
    """Extract Flask resources with their methods and rough paths"""
    resources = {}
    
    with open(resources_file, 'r') as f:
        content = f.read()
    
    # Find class definitions and their methods
    class_pattern = r'class\s+(\w+Resource)\(BaseMethodView\):'
    method_pattern = r'def\s+(get|post|put|patch|delete)\s*\('
    
    classes = list(re.finditer(class_pattern, content))
    
    for i, match in enumerate(classes):
        class_name = match.group(1)
        start = match.start()
        end = classes[i+1].start() if i+1 < len(classes) else len(content)
        
        class_content = content[start:end]
        methods = re.findall(method_pattern, class_content)
        
        resources[class_name] = [m.upper() for m in methods]
    
    return resources


def get_fastapi_endpoints_detailed(api_dir):
    """Extract FastAPI endpoints with details"""
    endpoints_by_file = defaultdict(list)
    
    for file in Path(api_dir).glob('async_*.py'):
        with open(file, 'r') as f:
            content = f.read()
        
        # Find all router decorators
        pattern = r'@router\.(get|post|put|patch|delete)\("([^"]+)".*?\)\s*async\s+def\s+(\w+)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for method, path, func_name in matches:
            endpoints_by_file[file.name].append({
                'method': method.upper(),
                'path': path,
                'function': func_name
            })
    
    return endpoints_by_file


def main():
    resources_file = Path(__file__).parent.parent / 'rotkehlchen/api/v1/resources.py'
    api_dir = Path(__file__).parent.parent / 'rotkehlchen/api/v1'
    
    flask_resources = get_flask_resources_detailed(resources_file)
    fastapi_endpoints = get_fastapi_endpoints_detailed(api_dir)
    
    # Analyze missing endpoints
    print("🔍 Missing Endpoints Analysis\n")
    
    missing_resources = []
    partial_resources = []
    complete_resources = []
    
    for resource_name, methods in sorted(flask_resources.items()):
        expected_file = RESOURCE_MAPPING.get(resource_name, 'Unknown')
        
        if expected_file == 'Unknown':
            missing_resources.append((resource_name, methods))
        else:
            # Check if file exists and has the expected number of methods
            if expected_file in fastapi_endpoints:
                fastapi_count = len(fastapi_endpoints[expected_file])
                flask_count = len(methods)
                
                if fastapi_count >= flask_count:
                    complete_resources.append((resource_name, methods, expected_file))
                else:
                    partial_resources.append((resource_name, methods, expected_file, fastapi_count))
            else:
                missing_resources.append((resource_name, methods))
    
    # Print results
    print(f"✅ Complete Resources ({len(complete_resources)}):")
    for name, methods, file in complete_resources[:10]:  # Show first 10
        print(f"  {name}: {', '.join(methods)} → {file}")
    if len(complete_resources) > 10:
        print(f"  ... and {len(complete_resources) - 10} more")
    
    print(f"\n⚠️  Partial Resources ({len(partial_resources)}):")
    for name, methods, file, count in partial_resources:
        print(f"  {name}: {', '.join(methods)} ({len(methods)} methods) → {file} (has {count} endpoints)")
    
    print(f"\n❌ Missing Resources ({len(missing_resources)}):")
    total_missing_methods = 0
    for name, methods in missing_resources:
        total_missing_methods += len(methods)
        print(f"  {name}: {', '.join(methods)} ({len(methods)} methods)")
    
    print(f"\n📊 Summary:")
    print(f"  Total Flask resources: {len(flask_resources)}")
    print(f"  Complete: {len(complete_resources)}")
    print(f"  Partial: {len(partial_resources)}")
    print(f"  Missing: {len(missing_resources)}")
    print(f"  Total missing methods: {total_missing_methods}")
    
    # Show which files need work
    print("\n📝 Files that need additional endpoints:")
    files_needing_work = defaultdict(list)
    
    for name, methods, file, count in partial_resources:
        files_needing_work[file].append((name, len(methods) - count))
    
    for file, resources in sorted(files_needing_work.items()):
        total_needed = sum(count for _, count in resources)
        print(f"\n  {file} (needs {total_needed} more endpoints):")
        for name, count in resources:
            print(f"    - {name}: {count} methods missing")


if __name__ == '__main__':
    main()