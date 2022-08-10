import { defineAsyncComponent } from '@vue/composition-api';
import Vue from 'vue';
import {
  VAlert,
  VBtn,
  VBtnToggle,
  VCol,
  VColorPicker,
  VContainer,
  VDataTableHeader,
  VDialog,
  VDivider,
  VForm,
  VIcon,
  VRow,
  VSimpleTable,
  VSpacer,
  VTextField,
  VTooltip
} from 'vuetify/lib/components';
const AssetLink = defineAsyncComponent(
  () => import('@/components/assets/AssetLink.vue')
);
const PaginatedCards = defineAsyncComponent(
  () => import('@/components/common/PaginatedCards.vue')
);
const ExportSnapshotDialog = defineAsyncComponent(
  () => import('@/components/dashboard/ExportSnapshotDialog.vue')
);
const DefiProtocolIcon = defineAsyncComponent(
  () => import('@/components/defi/display/DefiProtocolIcon.vue')
);
const UniswapPoolDetails = defineAsyncComponent(
  () => import('@/components/defi/uniswap/UniswapPoolDetails.vue')
);
const ConfirmDialog = defineAsyncComponent(
  () => import('@/components/dialogs/ConfirmDialog.vue')
);
const DateTimePicker = defineAsyncComponent(
  () => import('@/components/dialogs/DateTimePicker.vue')
);
const AmountDisplay = defineAsyncComponent(
  () => import('@/components/display/AmountDisplay.vue')
);
const AssetMovementDisplay = defineAsyncComponent(
  () => import('@/components/display/AssetMovementDisplay.vue')
);
const BalanceDisplay = defineAsyncComponent(
  () => import('@/components/display/BalanceDisplay.vue')
);
const DateDisplay = defineAsyncComponent(
  () => import('@/components/display/DateDisplay.vue')
);
const EventTypeDisplay = defineAsyncComponent(
  () => import('@/components/display/EventTypeDisplay.vue')
);
const BalancerPoolAsset = defineAsyncComponent(
  () => import('@/components/display/icons/BalancerPoolAsset.vue')
);
const UniswapPoolAsset = defineAsyncComponent(
  () => import('@/components/display/icons/UniswapPoolAsset.vue')
);
const PercentageDisplay = defineAsyncComponent(
  () => import('@/components/display/PercentageDisplay.vue')
);
const GraphTooltipWrapper = defineAsyncComponent(
  () => import('@/components/graphs/GraphTooltipWrapper.vue')
);
const AssetDetails = defineAsyncComponent(
  () => import('@/components/helper/AssetDetails.vue')
);
const BlockchainAccountSelector = defineAsyncComponent(
  () => import('@/components/helper/BlockchainAccountSelector.vue')
);
const Card = defineAsyncComponent(() => import('@/components/helper/Card.vue'));
const DataTable = defineAsyncComponent(
  () => import('@/components/helper/DataTable.vue')
);
const RangeSelector = defineAsyncComponent(
  () => import('@/components/helper/date/RangeSelector.vue')
);
const AssetIcon = defineAsyncComponent(
  () => import('@/components/helper/display/icons/AssetIcon.vue')
);
const HashLink = defineAsyncComponent(
  () => import('@/components/helper/HashLink.vue')
);
const LiquidityPoolSelector = defineAsyncComponent(
  () => import('@/components/helper/LiquidityPoolSelector.vue')
);
const MenuTooltipButton = defineAsyncComponent(
  () => import('@/components/helper/MenuTooltipButton.vue')
);
const RefreshHeader = defineAsyncComponent(
  () => import('@/components/helper/RefreshHeader.vue')
);
const TableExpandContainer = defineAsyncComponent(
  () => import('@/components/helper/table/TableExpandContainer.vue')
);
const TableFilter = defineAsyncComponent(
  () => import('@/components/history/filtering/TableFilter.vue')
);
const LocationDisplay = defineAsyncComponent(
  () => import('@/components/history/LocationDisplay.vue')
);
const TradeLocationSelector = defineAsyncComponent(
  () => import('@/components/history/TradeLocationSelector.vue')
);
const AmountInput = defineAsyncComponent(
  () => import('@/components/inputs/AmountInput.vue')
);
const AssetSelect = defineAsyncComponent(
  () => import('@/components/inputs/AssetSelect.vue')
);
const StatisticsGraphSettings = defineAsyncComponent(
  () => import('@/components/settings/StatisticsGraphSettings.vue')
);
const CardTitle = defineAsyncComponent(
  () => import('@/components/typography/CardTitle.vue')
);

/**
 * Vuetify components that are used in the premium components
 */
const vuetifyRegister = () => {
  // version 17 - 1.24
  Vue.component('VCol', VCol);
  Vue.component('VRow', VRow);
  Vue.component('VTooltip', VTooltip);
  Vue.component('VTextField', VTextField);
  Vue.component('VIcon', VIcon);
  Vue.component('VBtn', VBtn);
  Vue.component('VBtnToggle', VBtnToggle);
  Vue.component('VAlert', VAlert);
  Vue.component('VContainer', VContainer);
  Vue.component('VSimpleTable', VSimpleTable);
  Vue.component('VDialog', VDialog);
  Vue.component('VDivider', VDivider);
  Vue.component('VForm', VForm);
  Vue.component('VSpacer', VSpacer);
  Vue.component('VColorPicker', VColorPicker);
  Vue.component('VDataTableHeader', VDataTableHeader);
};

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
  Vue.component('TableFilter', TableFilter);
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
  // Version 17 - 1.24
  Vue.component('ExportSnapshotDialog', ExportSnapshotDialog);
  // Version 18 - 1.25
  Vue.component('MenuTooltipButton', MenuTooltipButton);
  Vue.component('GraphTooltipWrapper', GraphTooltipWrapper);
  vuetifyRegister();
}
