/* eslint-disable import/max-dependencies */
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
  RuiProgress,
  RuiSlider,
  RuiTextField,
  RuiTooltip,
} from '@rotki/ui-library';
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
import RefreshButton from '@/components/helper/RefreshButton.vue';
import type { App } from 'vue';

function ruiRegister(app: App): void {
  app.component('RuiAlert', RuiAlert);
  app.component('RuiIcon', RuiIcon);
  app.component('RuiButton', RuiButton);
  app.component('RuiTooltip', RuiTooltip);
  app.component('RuiTextField', RuiTextField);
  app.component('RuiButtonGroup', RuiButtonGroup);
  app.component('RuiCard', RuiCard);
  app.component('RuiDataTable', RuiDataTable);
  app.component('RuiDivider', RuiDivider);
  app.component('RuiChip', RuiChip);
  app.component('RuiMenu', RuiMenu);
  app.component('RuiSlider', RuiSlider);
  app.component('RuiDialog', RuiDialog);
  app.component('RuiColorPicker', RuiColorPicker);
  app.component('RuiProgress', RuiProgress);
}

export function registerComponents(app: App): void {
  // Globally registered components are also provided to the premium components.
  app.component('AmountDisplay', AmountDisplay);
  // version: 1
  app.component('HashLink', HashLink);
  app.component('AssetDetails', AssetDetails);
  app.component('DefiProtocolIcon', DefiProtocolIcon);
  // version: 2
  //  CryptoIcon was replaced with AssetIcon on v11
  app.component('BalanceDisplay', BalanceDisplay);
  // version: 3
  app.component('PercentageDisplay', PercentageDisplay);
  // version: 4
  app.component('BlockchainAccountSelector', BlockchainAccountSelector);
  app.component('DateDisplay', DateDisplay);
  app.component('LocationDisplay', LocationDisplay);
  // version 5
  app.component('AssetSelect', AssetSelect);
  // version 6
  app.component('DateTimePicker', DateTimePicker);
  // version 8
  app.component('CardTitle', CardTitle);
  // version 9
  app.component('LiquidityPoolSelector', LiquidityPoolSelector);
  app.component('TableFilter', TableFilter);
  // version 11
  app.component('AssetIcon', AssetIcon);
  // version 12 - 1.19
  app.component('RangeSelector', RangeSelector);
  app.component('ConfirmDialog', ConfirmDialog);
  // Version 13 - 1.20
  app.component('UniswapPoolDetails', UniswapPoolDetails);
  // Version 14 - 1.21
  app.component('PaginatedCards', PaginatedCards);
  app.component('AssetLink', AssetLink);
  // Version 15 - 1.21.2
  app.component('StatisticsGraphSettings', StatisticsGraphSettings);
  // Version 16 - 1.23
  app.component('AmountInput', AmountInput);
  // Version 17 - 1.24
  app.component('ExportSnapshotDialog', ExportSnapshotDialog);
  // Version 18 - 1.25
  app.component('MenuTooltipButton', MenuTooltipButton);
  app.component('GraphTooltipWrapper', GraphTooltipWrapper);
  // Version 19 - 1.26
  app.component('LpPoolIcon', LpPoolIcon);
  // Version 20 - 1.27
  app.component('BadgeDisplay', BadgeDisplay);
  // Version 21 - 1.28
  app.component('HistoryEventsView', HistoryEventsView);
  // Version 24 - 1.31
  app.component('LpPoolHeader', LpPoolHeader);
  app.component('RowAppend', RowAppend);
  // Version 25 - 1.32
  app.component('UniswapPoolAssetBalance', UniswapPoolAssetBalance);
  // Version 26 - 1.34
  app.component('RefreshButton', RefreshButton);
  ruiRegister(app);
  logger.info('Components registered');
}
