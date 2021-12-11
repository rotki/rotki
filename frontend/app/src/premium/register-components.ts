import Vue from 'vue';
import AssetLink from '@/components/assets/AssetLink.vue';
import PaginatedCards from '@/components/common/PaginatedCards.vue';
import DefiProtocolIcon from '@/components/defi/display/DefiProtocolIcon.vue';
import UniswapPoolDetails from '@/components/defi/uniswap/UniswapPoolDetails.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetMovementDisplay from '@/components/display/AssetMovementDisplay.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import EventTypeDisplay from '@/components/display/EventTypeDisplay.vue';
import BalancerPoolAsset from '@/components/display/icons/BalancerPoolAsset.vue';
import UniswapPoolAsset from '@/components/display/icons/UniswapPoolAsset.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import Card from '@/components/helper/Card.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RangeSelector from '@/components/helper/date/RangeSelector.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import HashLink from '@/components/helper/HashLink.vue';
import LiquidityPoolSelector from '@/components/helper/LiquidityPoolSelector.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import TradeLocationSelector from '@/components/history/TradeLocationSelector.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import StatisticsGraphSettings from '@/components/settings/StatisticsGraphSettings.vue';
import CardTitle from '@/components/typography/CardTitle.vue';

export function registerComponents() {
  // Globally registered components are also provided to the premium components.
  Vue.component('AmountDisplay', AmountDisplay);
  // version: 1
  Vue.component('HashLink', HashLink);
  Vue.component('AssetDetails', AssetDetails);
  Vue.component('DefiProtocolIcon', DefiProtocolIcon);
  // version: 2
  Vue.component('AssetMovementDisplay', AssetMovementDisplay);
  Vue.component('EventTypeDisplay', EventTypeDisplay);
  //  CryptoIcon was replaced with AssetIcon on v11
  Vue.component('BalanceDisplay', BalanceDisplay);
  // version: 3
  Vue.component('PercentageDisplay', PercentageDisplay);
  // version: 4
  Vue.component('BlockchainAccountSelector', BlockchainAccountSelector);
  Vue.component('DateDisplay', DateDisplay);
  Vue.component('LocationDisplay', LocationDisplay);
  Vue.component('RefreshHeader', RefreshHeader);
  Vue.component('UniswapPoolAsset', UniswapPoolAsset);
  // version 5
  Vue.component('AssetSelect', AssetSelect);
  // version 6
  Vue.component('DateTimePicker', DateTimePicker);
  // version 8
  Vue.component('CardTitle', CardTitle);
  // version 9
  Vue.component('Card', Card);
  Vue.component('LiquidityPoolSelector', LiquidityPoolSelector);
  Vue.component('BalancerPoolAsset', BalancerPoolAsset);
  Vue.component('TradeLocationSelector', TradeLocationSelector);
  // version 10
  Vue.component('DataTable', DataTable);
  Vue.component('TableExpandContainer', TableExpandContainer);
  // version 11
  Vue.component('AssetIcon', AssetIcon);
  // version 12 - 1.19
  Vue.component('RangeSelector', RangeSelector);
  Vue.component('ConfirmDialog', ConfirmDialog);
  // Version 13 - 1.20
  Vue.component('UniswapPoolDetails', UniswapPoolDetails);
  // Version 14 - 1.21
  Vue.component('PaginatedCards', PaginatedCards);
  Vue.component('AssetLink', AssetLink);
  // Version 15 - 1.21.2
  Vue.component('StatisticsGraphSettings', StatisticsGraphSettings);
  // Version 16 - 1.23
  Vue.component('AmountInput', AmountInput);
}
