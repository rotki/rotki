/* eslint-disable import/max-dependencies */

import Vue from 'vue';
import {
  VColorPicker,
  VDialog,
} from 'vuetify/lib/components';
import {
  RuiAlert,
  RuiButton,
  RuiButtonGroup,
  RuiCard,
  RuiChip,
  RuiColorPicker,
  RuiDataTable,
  RuiDialog,
  RuiDivider,
  RuiIcon,
  RuiMenu,
  RuiSlider,
  RuiTextField,
  RuiTooltip,
} from '@rotki/ui-library-compat';
import AssetLink from '@/components/assets/AssetLink.vue';
import PaginatedCards from '@/components/common/PaginatedCards.vue';
import ExportSnapshotDialog from '@/components/dashboard/ExportSnapshotDialog.vue';
import DefiProtocolIcon from '@/components/defi/display/DefiProtocolIcon.vue';
import UniswapPoolDetails from '@/components/defi/uniswap/UniswapPoolDetails.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import LpPoolIcon from '@/components/display/defi/LpPoolIcon.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import GraphTooltipWrapper from '@/components/graphs/GraphTooltipWrapper.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import RangeSelector from '@/components/helper/date/RangeSelector.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import HashLink from '@/components/helper/HashLink.vue';
import LiquidityPoolSelector from '@/components/helper/LiquidityPoolSelector.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import StatisticsGraphSettings from '@/components/settings/StatisticsGraphSettings.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import HistoryEventsView from '@/components/history/events/HistoryEventsView.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LpPoolHeader from '@/components/display/defi/LpPoolHeader.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import UniswapPoolAssetBalance from '@/components/defi/uniswap/UniswapPoolAssetBalance.vue';

/**
 * Vuetify components that are used in the premium components
 */
function vuetifyRegister(): void {
  // version 17 - 1.24
  Vue.component('VDialog', VDialog);
  Vue.component('VColorPicker', VColorPicker);
}

function ruiRegister(): void {
  Vue.component('RuiAlert', RuiAlert);
  Vue.component('RuiIcon', RuiIcon);
  Vue.component('RuiButton', RuiButton);
  Vue.component('RuiTooltip', RuiTooltip);
  Vue.component('RuiTextField', RuiTextField);
  Vue.component('RuiButtonGroup', RuiButtonGroup);
  Vue.component('RuiCard', RuiCard);
  Vue.component('RuiDataTable', RuiDataTable);
  Vue.component('RuiDivider', RuiDivider);
  Vue.component('RuiChip', RuiChip);
  Vue.component('RuiMenu', RuiMenu);
  Vue.component('RuiSlider', RuiSlider);
  Vue.component('RuiDialog', RuiDialog);
  Vue.component('RuiColorPicker', RuiColorPicker);
}

export function registerComponents(): void {
  // Globally registered components are also provided to the premium components.
  Vue.component('AmountDisplay', AmountDisplay);
  // version: 1
  Vue.component('HashLink', HashLink);
  Vue.component('AssetDetails', AssetDetails);
  Vue.component('DefiProtocolIcon', DefiProtocolIcon);
  // version: 2
  //  CryptoIcon was replaced with AssetIcon on v11
  Vue.component('BalanceDisplay', BalanceDisplay);
  // version: 3
  Vue.component('PercentageDisplay', PercentageDisplay);
  // version: 4
  Vue.component('BlockchainAccountSelector', BlockchainAccountSelector);
  Vue.component('DateDisplay', DateDisplay);
  Vue.component('LocationDisplay', LocationDisplay);
  // version 5
  Vue.component('AssetSelect', AssetSelect);
  // version 6
  Vue.component('DateTimePicker', DateTimePicker);
  // version 8
  Vue.component('CardTitle', CardTitle);
  // version 9
  Vue.component('LiquidityPoolSelector', LiquidityPoolSelector);
  Vue.component('TableFilter', TableFilter);
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
  // Version 19 - 1.26
  Vue.component('LpPoolIcon', LpPoolIcon);
  // Version 20 - 1.27
  Vue.component('BadgeDisplay', BadgeDisplay);
  // Version 21 - 1.28
  Vue.component('HistoryEventsView', HistoryEventsView);
  // Version 24 - 1.31
  Vue.component('LpPoolHeader', LpPoolHeader);
  Vue.component('RowAppend', RowAppend);
  // Version 25 - 1.32
  Vue.component('UniswapPoolAssetBalance', UniswapPoolAssetBalance);
  vuetifyRegister();
  ruiRegister();
  logger.info('Components registered');
}
