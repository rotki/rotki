<template>
  <v-dialog
    v-model="open"
    max-width="800"
    open-delay="100"
    height="400"
    :content-class="$style.dialog"
    transition="slide-y-transition"
  >
    <template #activator="{ on }">
      <menu-tooltip-button
        class-name="secondary--text text--lighten-4"
        :tooltip="
          $t('global_search.menu_tooltip', {
            modifier,
            key
          }).toString()
        "
        :on-menu="on"
      >
        <v-icon>mdi-magnify</v-icon>
      </menu-tooltip-button>
    </template>
    <div :class="$style.wrapper">
      <v-autocomplete
        ref="input"
        v-model="selected"
        no-filter
        filled
        :no-data-text="$tc('global_search.no_actions')"
        :search-input.sync="search"
        :background-color="dark ? 'black' : 'white'"
        hide-details
        :items="filteredItems"
        auto-select-first
        prepend-inner-icon="mdi-magnify"
        append-icon=""
        :placeholder="$tc('global_search.search_placeholder')"
        @input="change"
      >
        <template #item="{ item }">
          <div
            class="d-flex align-center text-body-2"
            :class="$style['full-width']"
          >
            <asset-icon
              v-if="item.asset"
              size="30px"
              :identifier="item.asset"
            />
            <adaptive-wrapper v-else component="span">
              <location-icon
                v-if="item.location"
                icon
                no-padding
                size="26px"
                :item="item.location"
              />
              <v-img
                v-else-if="item.image"
                width="30"
                max-height="30"
                contain
                position="left"
                :src="item.image"
              />
              <v-icon v-else size="30" color="grey">
                {{ item.icon }}
              </v-icon>
            </adaptive-wrapper>
            <span class="ml-3">
              <template v-if="item.texts">
                <span v-for="(text, index) in item.texts" :key="text + index">
                  <span v-if="index === item.texts.length - 1">{{ text }}</span>
                  <span v-else class="grey--text">
                    {{ text }}<v-icon small> mdi-chevron-right </v-icon>
                  </span>
                </span>
              </template>
              <template v-else>
                {{ item.text }}
              </template>
            </span>
            <v-spacer />
            <div v-if="item.price" class="text-right">
              <div class="text-caption">{{ $tc('common.price') }}:</div>
              <amount-display
                class="font-weight-bold"
                :fiat-currency="currencySymbol"
                :value="item.price"
              />
            </div>
            <div v-if="item.total" class="text-right">
              <div class="text-caption">{{ $tc('common.total') }}:</div>
              <amount-display
                class="font-weight-bold"
                :fiat-currency="currencySymbol"
                :value="item.total"
              />
            </div>
          </div>
        </template>
      </v-autocomplete>
    </div>
  </v-dialog>
</template>
<script lang="ts">
import { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  nextTick,
  onBeforeMount,
  ref,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { TradeLocationData } from '@/components/history/type';
import { setupLocationInfo } from '@/composables/balances';
import { useRouter, useTheme } from '@/composables/common';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { routesRef } from '@/router/routes';
import { useAssetInfoRetrieval } from '@/store/assets';
import { useBalancesStore } from '@/store/balances';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Exchange } from '@/types/exchanges';

type SearchItem = {
  value: number;
  text?: string;
  texts?: string[];
  asset?: string;
  location?: TradeLocationData;
  price?: BigNumber;
  total?: BigNumber;
  icon?: string;
  image?: string;
  route?: string;
  action?: Function;
  matchedPoints?: number;
};

type SearchItemWithoutValue = Omit<SearchItem, 'value'>;

export default defineComponent({
  name: 'GlobalSearch',
  components: { LocationIcon, AdaptiveWrapper, MenuTooltipButton },
  setup() {
    const Routes = get(routesRef);
    const open = ref<boolean>(false);
    const isMac = ref<boolean>(false);

    const input = ref<any>(null);
    const selected = ref<number | string>('');
    const search = ref<string>('');

    const modifier = computed<string>(() => (get(isMac) ? 'Cmd' : 'Ctrl'));
    const key = '/';

    const router = useRouter();

    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
    const { assetSymbol } = useAssetInfoRetrieval();
    const { connectedExchanges } = storeToRefs(useExchangeBalancesStore());
    const { aggregatedBalances } = storeToRefs(useBlockchainBalancesStore());
    const { balancesByLocation } = storeToRefs(useBalancesStore());
    const { getLocation } = setupLocationInfo();
    const { dark } = useTheme();

    const items = computed<SearchItem[]>(() => {
      const routeItems: SearchItemWithoutValue[] = [
        { ...Routes.DASHBOARD },
        {
          ...Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
          texts: [
            Routes.ACCOUNTS_BALANCES.text,
            Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.text
          ]
        },
        {
          ...Routes.ACCOUNTS_BALANCES_EXCHANGE,
          texts: [
            Routes.ACCOUNTS_BALANCES.text,
            Routes.ACCOUNTS_BALANCES_EXCHANGE.text
          ]
        },
        {
          ...Routes.ACCOUNTS_BALANCES_MANUAL,
          texts: [
            Routes.ACCOUNTS_BALANCES.text,
            Routes.ACCOUNTS_BALANCES_MANUAL.text
          ]
        },
        {
          ...Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE,
          texts: [
            Routes.ACCOUNTS_BALANCES.text,
            Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE.text
          ]
        },
        { ...Routes.NFTS },
        {
          ...Routes.HISTORY_TRADES,
          texts: [Routes.HISTORY.text, Routes.HISTORY_TRADES.text]
        },
        {
          ...Routes.HISTORY_DEPOSITS_WITHDRAWALS,
          texts: [Routes.HISTORY.text, Routes.HISTORY_DEPOSITS_WITHDRAWALS.text]
        },
        {
          ...Routes.HISTORY_TRANSACTIONS,
          texts: [Routes.HISTORY.text, Routes.HISTORY_TRANSACTIONS.text]
        },
        {
          ...Routes.HISTORY_LEDGER_ACTIONS,
          texts: [Routes.HISTORY.text, Routes.HISTORY_LEDGER_ACTIONS.text]
        },
        {
          ...Routes.DEFI_OVERVIEW,
          texts: [Routes.DEFI.text, Routes.DEFI_OVERVIEW.text]
        },
        {
          ...Routes.DEFI_DEPOSITS_PROTOCOLS,
          texts: [
            Routes.DEFI.text,
            Routes.DEFI_DEPOSITS.text,
            Routes.DEFI_DEPOSITS_PROTOCOLS.text
          ]
        },
        {
          ...Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2,
          texts: [
            Routes.DEFI.text,
            Routes.DEFI_DEPOSITS.text,
            Routes.DEFI_DEPOSITS_LIQUIDITY.text,
            Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2.text
          ]
        },
        {
          ...Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3,
          texts: [
            Routes.DEFI.text,
            Routes.DEFI_DEPOSITS.text,
            Routes.DEFI_DEPOSITS_LIQUIDITY.text,
            Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3.text
          ]
        },
        {
          ...Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER,
          texts: [
            Routes.DEFI.text,
            Routes.DEFI_DEPOSITS.text,
            Routes.DEFI_DEPOSITS_LIQUIDITY.text,
            Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER.text
          ]
        },
        {
          ...Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP,
          texts: [
            Routes.DEFI.text,
            Routes.DEFI_DEPOSITS.text,
            Routes.DEFI_DEPOSITS_LIQUIDITY.text,
            Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP.text
          ]
        },
        {
          ...Routes.DEFI_LIABILITIES,
          texts: [Routes.DEFI.text, Routes.DEFI_LIABILITIES.text]
        },
        {
          ...Routes.DEFI_DEX_TRADES,
          texts: [Routes.DEFI.text, Routes.DEFI_DEX_TRADES.text]
        },
        {
          ...Routes.DEFI_AIRDROPS,
          texts: [Routes.DEFI.text, Routes.DEFI_AIRDROPS.text]
        },
        { ...Routes.STATISTICS },
        { ...Routes.STAKING },
        { ...Routes.PROFIT_LOSS_REPORTS },
        { ...Routes.ASSET_MANAGER },
        { ...Routes.PRICE_MANAGER },
        { ...Routes.ETH_ADDRESS_BOOK_MANAGER },
        {
          ...Routes.API_KEYS_ROTKI_PREMIUM,
          texts: [Routes.API_KEYS.text, Routes.API_KEYS_ROTKI_PREMIUM.text]
        },
        {
          ...Routes.API_KEYS_EXCHANGES,
          texts: [Routes.API_KEYS.text, Routes.API_KEYS_EXCHANGES.text]
        },
        {
          ...Routes.API_KEYS_EXTERNAL_SERVICES,
          texts: [Routes.API_KEYS.text, Routes.API_KEYS_EXTERNAL_SERVICES.text]
        },
        { ...Routes.IMPORT },
        {
          ...Routes.SETTINGS_GENERAL,
          texts: [Routes.SETTINGS.text, Routes.SETTINGS_GENERAL.text]
        },
        {
          ...Routes.SETTINGS_ACCOUNTING,
          texts: [Routes.SETTINGS.text, Routes.SETTINGS_ACCOUNTING.text]
        },
        {
          ...Routes.SETTINGS_DATA_SECURITY,
          texts: [Routes.SETTINGS.text, Routes.SETTINGS_DATA_SECURITY.text]
        },
        {
          ...Routes.SETTINGS_MODULES,
          texts: [Routes.SETTINGS.text, Routes.SETTINGS_MODULES.text]
        }
      ];

      const exchangeItems: SearchItemWithoutValue[] = get(
        connectedExchanges
      ).map((exchange: Exchange) => {
        const identifier = exchange.location;
        const name = exchange.name;

        return {
          location: getLocation(identifier),
          route: `${Routes.ACCOUNTS_BALANCES_EXCHANGE.route}/${identifier}`,
          texts: [
            Routes.ACCOUNTS_BALANCES.text,
            Routes.ACCOUNTS_BALANCES_EXCHANGE.text,
            name
          ]
        };
      });

      const actionItems: SearchItemWithoutValue[] = [
        {
          text: i18n.t('exchange_settings.dialog.add.title').toString(),
          route: `${Routes.API_KEYS_EXCHANGES.route}?add=true`,
          icon: 'mdi-wallet-plus'
        },
        {
          text: i18n.t('blockchain_balances.form_dialog.add_title').toString(),
          route: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.route}?add=true`,
          icon: 'mdi-lock-open-plus'
        },
        {
          text: i18n.t('manual_balances.dialog.add.title').toString(),
          route: `${Routes.ACCOUNTS_BALANCES_MANUAL.route}?add=true`,
          icon: 'mdi-note-plus'
        },
        {
          text: i18n.t('closed_trades.dialog.add.title').toString(),
          route: `${Routes.HISTORY_TRADES.route}?add=true`,
          icon: 'mdi-plus-box-multiple'
        },
        {
          text: i18n.t('ledger_actions.dialog.add.title').toString(),
          route: `${Routes.HISTORY_LEDGER_ACTIONS.route}?add=true`,
          icon: 'mdi-text-box-plus'
        },
        {
          text: i18n.t('asset_management.add_title').toString(),
          route: `${Routes.ASSET_MANAGER.route}?add=true`,
          icon: 'mdi-plus-circle-multiple-outline'
        },
        {
          text: i18n.t('price_management.dialog.add_title').toString(),
          route: `${Routes.PRICE_MANAGER.route}?add=true`,
          icon: 'mdi-database-plus'
        }
      ];

      const assetItems: SearchItemWithoutValue[] = (
        get(aggregatedBalances) as AssetBalanceWithPrice[]
      ).map(balance => {
        const price = balance.usdPrice.gt(0) ? balance.usdPrice : undefined;
        const asset = balance.asset;

        return {
          route: Routes.ASSETS.route.replace(':identifier', asset),
          texts: [i18n.t('common.asset').toString(), get(assetSymbol(asset))],
          price,
          asset
        };
      });

      const locationBalances = get(balancesByLocation) as Record<
        string,
        BigNumber
      >;
      const locationItems: SearchItemWithoutValue[] = Object.keys(
        locationBalances
      ).map(identifier => {
        const total = locationBalances?.[identifier] ?? undefined;

        const location: TradeLocationData = getLocation(identifier);

        return {
          route: Routes.LOCATIONS.route.replace(
            ':identifier',
            location.identifier
          ),
          texts: [i18n.t('common.location').toString(), location.name],
          location,
          total
        };
      });

      return [
        ...routeItems,
        ...exchangeItems,
        ...actionItems,
        ...assetItems,
        ...locationItems
      ].map((item, index) => {
        const text = item.texts ? item.texts.join(' ') : item.text;
        return {
          ...item,
          value: index,
          text: text
            ?.replace(/[^\w\s]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim()
        };
      });
    });

    const filteredItems = computed<SearchItem[]>(() => {
      const keyword = get(search)?.toLowerCase() ?? '';
      if (!keyword) {
        return get(items);
      }

      // Filter items text by checking how many word on keyword that appear.
      return get(items)
        .filter(item => {
          let matchedPoints: number = 0;
          keyword
            .trim()
            .split(' ')
            .forEach(word => {
              const indexOf = item.text!.toLowerCase().indexOf(word);
              if (indexOf > -1) matchedPoints++;
              if (indexOf === 0) matchedPoints += 0.5;
            });
          item.matchedPoints = matchedPoints;
          return matchedPoints > 0;
        })
        .sort((a, b) => (b.matchedPoints ?? 0) - (a.matchedPoints ?? 0));
    });

    watch(search, () => {
      const el = get(input)?.$el;
      if (el) {
        const className = 'v-list-item--highlighted';
        const highlighted = el.querySelectorAll(`.${className}`).length;
        if (highlighted === 0) {
          nextTick(() => {
            const elementToUpdate = el.querySelectorAll('.v-list-item');
            if (elementToUpdate.length > 0) {
              elementToUpdate[0].classList.add(className);
            }
          });
        }
      }
    });

    watch(open, open => {
      nextTick(() => {
        if (open) {
          setTimeout(() => {
            get(input)?.$refs?.input?.focus?.();
          }, 100);
        }
        set(selected, '');
        set(search, '');
      });
    });

    const change = (index: number) => {
      const item: SearchItem = get(items)[index];
      if (item) {
        if (item.route) {
          router.push(item.route);
        }
        item?.action?.();
        set(open, false);
      }
    };

    onBeforeMount(async () => {
      set(isMac, await interop.isMac());

      window.addEventListener('keydown', async event => {
        // Mac use Command, Others use Control
        if (
          ((get(isMac) && event.metaKey) || (!get(isMac) && event.ctrlKey)) &&
          event.key === key
        ) {
          set(open, true);
        }
      });
    });

    return {
      dark,
      currencySymbol,
      input,
      filteredItems,
      selected,
      search,
      change,
      modifier,
      key,
      open
    };
  }
});
</script>
<style module lang="scss">
.full-width {
  width: 100%;
}

.dialog {
  margin-top: 200px;
  align-self: flex-start;
  box-shadow: none !important;
  overflow: visible !important;
}
</style>
