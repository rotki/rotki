import {
  VBtn,
  VBtnToggle,
  VColorPicker,
  VDialog,
  VIcon,
  VMenu,
  VSlider,
} from 'vuetify/components';
import { RuiAlert, RuiButton, RuiButtonGroup, RuiCard, RuiChip, RuiDataTable, RuiDivider, RuiIcon, RuiTextField, RuiTooltip } from '@rotki/ui-library';
import LiquidityPoolSelector from '@/components/helper/LiquidityPoolSelector.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import DataTable from '@/components/helper/DataTable.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import RangeSelector from '@/components/helper/date/RangeSelector.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import UniswapPoolDetails from '@/components/defi/uniswap/UniswapPoolDetails.vue';
import PaginatedCards from '@/components/common/PaginatedCards.vue';
import AssetLink from '@/components/assets/AssetLink.vue';
import StatisticsGraphSettings from '@/components/settings/StatisticsGraphSettings.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import ExportSnapshotDialog from '@/components/dashboard/ExportSnapshotDialog.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import GraphTooltipWrapper from '@/components/graphs/GraphTooltipWrapper.vue';
import LpPoolIcon from '@/components/display/defi/LpPoolIcon.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import HistoryEventsView from '@/components/history/events/HistoryEventsView.vue';
import LpPoolHeader from '@/components/display/defi/LpPoolHeader.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import UniswapPoolAssetBalance from '@/components/defi/uniswap/UniswapPoolAssetBalance.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import HashLink from '@/components/helper/HashLink.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import DefiProtocolIcon from '@/components/defi/display/DefiProtocolIcon.vue';
import type { App } from 'vue';

/**
 * Vuetify components that are used in the premium components
 */
function vuetifyRegister(app: App): void {
  // version 17 - 1.24
  app.component('VIcon', VIcon);
  app.component('VBtn', VBtn);
  app.component('VBtnToggle', VBtnToggle);
  app.component('VDialog', VDialog);
  app.component('VColorPicker', VColorPicker);
  app.component('VSlider', VSlider);
  app.component('VMenu', VMenu);
}

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
  // version 10
  app.component('DataTable', DataTable);
  app.component('TableExpandContainer', TableExpandContainer);
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
  vuetifyRegister(app);
  ruiRegister(app);
  logger.info('Components registered');
}
