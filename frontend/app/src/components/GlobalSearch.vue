<script setup lang="ts">
import { useAppRoutes } from '@/router/routes';
import type { RuiIcons } from '@rotki/ui-library';
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { Exchange } from '@/types/exchanges';
import type { TradeLocationData } from '@/types/history/trade/location';
import type { RouteLocationRaw } from 'vue-router';

interface SearchItem {
  value: number;
  text?: string;
  texts?: string[];
  asset?: string;
  location?: TradeLocationData;
  price?: BigNumber;
  total?: BigNumber;
  icon?: RuiIcons;
  image?: string;
  route?: RouteLocationRaw;
  action?: () => void;
  matchedPoints?: number;
}

type SearchItemWithoutValue = Omit<SearchItem, 'value'>;

const { t } = useI18n();
const { appRoutes } = useAppRoutes();
const Routes = get(appRoutes);
const open = ref<boolean>(false);
const isMac = ref<boolean>(false);

const input = ref<any>(null);
const selected = ref<number>();
const search = ref<string>('');
const loading = ref(false);
const visibleItems = ref<SearchItem[]>([]);

const modifier = computed<string>(() => (get(isMac) ? 'Cmd' : 'Ctrl'));
const key = '/';

const router = useRouter();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { connectedExchanges } = storeToRefs(useExchangesStore());
const { balances } = useAggregatedBalances();
const { balancesByLocation } = useBalancesBreakdown();
const { getLocationData } = useLocations();
const { assetSearch } = useAssetInfoRetrieval();

function getItemText(item: SearchItemWithoutValue): string {
  const text = item.texts ? item.texts.join(' ') : item.text;
  return (
    text
      ?.replace(/[^\s\w]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim() ?? ''
  );
}

function filterItems(items: SearchItemWithoutValue[], keyword: string): SearchItemWithoutValue[] {
  const splittedKeyword = keyword.split(' ');
  return items.filter((item) => {
    let matchedPoints = 0;
    for (const word of splittedKeyword) {
      const indexOf = getItemText(item).toLowerCase().indexOf(word);
      if (indexOf > -1) {
        matchedPoints++;
        if (indexOf === 0)
          matchedPoints += 0.5;
      }
    }
    item.matchedPoints = matchedPoints;
    return matchedPoints > 0;
  });
}

function getRoutes(keyword: string): SearchItemWithoutValue[] {
  const routeItems: SearchItemWithoutValue[] = [
    { ...Routes.DASHBOARD },
    {
      ...Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
      texts: [Routes.ACCOUNTS_BALANCES.text, Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.text],
    },
    {
      ...Routes.ACCOUNTS_BALANCES_EXCHANGE,
      texts: [Routes.ACCOUNTS_BALANCES.text, Routes.ACCOUNTS_BALANCES_EXCHANGE.text],
    },
    {
      ...Routes.ACCOUNTS_BALANCES_MANUAL,
      texts: [Routes.ACCOUNTS_BALANCES.text, Routes.ACCOUNTS_BALANCES_MANUAL.text],
    },
    {
      ...Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE,
      texts: [Routes.ACCOUNTS_BALANCES.text, Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE.text],
    },
    { ...Routes.NFTS },
    {
      ...Routes.HISTORY_TRADES,
      texts: [Routes.HISTORY.text, Routes.HISTORY_TRADES.text],
    },
    {
      ...Routes.HISTORY_DEPOSITS_WITHDRAWALS,
      texts: [Routes.HISTORY.text, Routes.HISTORY_DEPOSITS_WITHDRAWALS.text],
    },
    {
      ...Routes.HISTORY_EVENTS,
      texts: [Routes.HISTORY.text, Routes.HISTORY_EVENTS.text],
    },
    {
      ...Routes.DEFI_OVERVIEW,
      texts: [Routes.DEFI.text, Routes.DEFI_OVERVIEW.text],
    },
    {
      ...Routes.DEFI_DEPOSITS_PROTOCOLS,
      texts: [Routes.DEFI.text, Routes.DEFI_DEPOSITS.text, Routes.DEFI_DEPOSITS_PROTOCOLS.text],
    },
    {
      ...Routes.DEFI_DEPOSITS_LIQUIDITY,
      texts: [Routes.DEFI.text, Routes.DEFI_DEPOSITS.text, Routes.DEFI_DEPOSITS_LIQUIDITY.text],
    },
    {
      ...Routes.DEFI_LIABILITIES,
      texts: [Routes.DEFI.text, Routes.DEFI_LIABILITIES.text],
    },
    {
      ...Routes.DEFI_AIRDROPS,
      texts: [Routes.DEFI.text, Routes.DEFI_AIRDROPS.text],
    },
    { ...Routes.STATISTICS },
    { ...Routes.STAKING },
    { ...Routes.PROFIT_LOSS_REPORTS },
    {
      ...Routes.ASSET_MANAGER_MANAGED,
      texts: [Routes.ASSET_MANAGER.text, Routes.ASSET_MANAGER_MANAGED.text],
    },
    {
      ...Routes.ASSET_MANAGER_CUSTOM,
      texts: [Routes.ASSET_MANAGER.text, Routes.ASSET_MANAGER_CUSTOM.text],
    },
    {
      ...Routes.ASSET_MANAGER_NEWLY_DETECTED,
      texts: [Routes.ASSET_MANAGER.text, Routes.ASSET_MANAGER_NEWLY_DETECTED.text],
    },
    {
      ...Routes.PRICE_MANAGER_LATEST,
      texts: [Routes.PRICE_MANAGER.text, Routes.PRICE_MANAGER_LATEST.text],
    },
    {
      ...Routes.PRICE_MANAGER_HISTORIC,
      texts: [Routes.PRICE_MANAGER.text, Routes.PRICE_MANAGER_HISTORIC.text],
    },
    { ...Routes.ADDRESS_BOOK_MANAGER },
    {
      ...Routes.API_KEYS_ROTKI_PREMIUM,
      texts: [Routes.API_KEYS.text, Routes.API_KEYS_ROTKI_PREMIUM.text],
    },
    {
      ...Routes.API_KEYS_EXCHANGES,
      texts: [Routes.API_KEYS.text, Routes.API_KEYS_EXCHANGES.text],
    },
    {
      ...Routes.API_KEYS_EXTERNAL_SERVICES,
      texts: [Routes.API_KEYS.text, Routes.API_KEYS_EXTERNAL_SERVICES.text],
    },
    { ...Routes.IMPORT },
    {
      ...Routes.SETTINGS_ACCOUNT,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_ACCOUNT.text],
    },
    {
      ...Routes.SETTINGS_GENERAL,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_GENERAL.text],
    },
    {
      ...Routes.SETTINGS_DATABASE,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_DATABASE.text],
    },
    {
      ...Routes.SETTINGS_ACCOUNTING,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_ACCOUNTING.text],
    },
    {
      ...Routes.SETTINGS_ORACLE,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_ORACLE.text],
    },
    {
      ...Routes.SETTINGS_RPC,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_RPC.text],
    },
    {
      ...Routes.SETTINGS_MODULES,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_MODULES.text],
    },
    {
      ...Routes.SETTINGS_INTERFACE,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_INTERFACE.text],
    },
    {
      ...Routes.CALENDAR,
    },
  ];

  return filterItems(routeItems, keyword);
}

function getExchanges(keyword: string): SearchItemWithoutValue[] {
  const exchanges = get(connectedExchanges);
  const exchangeItems: SearchItemWithoutValue[] = exchanges.map((exchange: Exchange) => {
    const identifier = exchange.location;
    const name = exchange.name;

    return {
      location: getLocationData(identifier) ?? undefined,
      route: `${Routes.ACCOUNTS_BALANCES_EXCHANGE.route}/${identifier}`,
      texts: [Routes.ACCOUNTS_BALANCES.text, Routes.ACCOUNTS_BALANCES_EXCHANGE.text, name],
    };
  });

  return filterItems(exchangeItems, keyword);
}

function getActions(keyword: string): SearchItemWithoutValue[] {
  const actionItems: SearchItemWithoutValue[] = [
    {
      text: t('exchange_settings.dialog.add.title'),
      route: `${Routes.API_KEYS_EXCHANGES.route}?add=true`,
    },
    {
      text: t('blockchain_balances.form_dialog.add_title'),
      route: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.route}?add=true`,
    },
    {
      text: t('manual_balances.dialog.add.title'),
      route: `${Routes.ACCOUNTS_BALANCES_MANUAL.route}?add=true`,
    },
    {
      text: t('closed_trades.dialog.add.title'),
      route: `${Routes.HISTORY_TRADES.route}?add=true`,
    },
    {
      text: t('asset_management.add_title'),
      route: `${Routes.ASSET_MANAGER.route}?add=true`,
    },
    {
      text: t('price_management.latest.add_title'),
      route: `${Routes.PRICE_MANAGER_LATEST.route}?add=true`,
    },
    {
      text: t('price_management.historic.add_title'),
      route: `${Routes.PRICE_MANAGER_HISTORIC.route}?add=true`,
    },
  ].map(item => ({ ...item, icon: 'add-circle-line' }));

  return filterItems(actionItems, keyword);
}

async function getAssets(keyword: string): Promise<SearchItemWithoutValue[]> {
  const matches = await assetSearch({
    value: keyword,
    limit: 5,
  });
  const assetBalances = get(balances()) as AssetBalanceWithPrice[];
  const map: Record<string, string> = {};
  for (const match of matches) map[match.identifier] = match.symbol ?? match.name ?? '';

  const ids = matches.map(({ identifier }) => identifier);

  return assetBalances
    .filter(balance => ids.includes(balance.asset))
    .map((balance) => {
      const price = balance.price.gt(0) ? balance.price : undefined;
      const asset = balance.asset;

      return {
        route: {
          name: '/assets/[identifier]',
          params: {
            identifier: asset,
          },
        },
        texts: [t('common.asset'), map[asset] ?? ''],
        price,
        asset,
      };
    });
}

function* transformLocations(): IterableIterator<SearchItemWithoutValue> {
  const locationBalances = get(balancesByLocation);

  for (const identifier in locationBalances) {
    const location = getLocationData(identifier);
    if (!location)
      continue;

    const total = locationBalances[identifier];
    yield {
      route: {
        name: '/locations/[identifier]',
        params: {
          identifier: encodeURIComponent(location.identifier),
        },
      },
      texts: [t('common.location'), location.name],
      location,
      total,
    } satisfies SearchItemWithoutValue;
  }
}

function getLocations(keyword: string) {
  return filterItems([...transformLocations()], keyword);
}

watchDebounced(
  search,
  async (keyword) => {
    if (!keyword) {
      set(visibleItems, []);
      return;
    }

    const search = keyword.toLocaleLowerCase().trim();

    const staticData = [
      ...getRoutes(search),
      ...getExchanges(search),
      ...getActions(search),
      ...getLocations(search),
    ].sort((a, b) => (b.matchedPoints ?? 0) - (a.matchedPoints ?? 0));

    set(
      visibleItems,
      [...staticData, ...(await getAssets(search))].map((item, index) => ({
        ...item,
        value: index,
        text: getItemText(item),
      })),
    );

    set(loading, false);
  },
  {
    debounce: 800,
  },
);

watch(search, (search) => {
  set(loading, !!search);
});

watch(open, (open) => {
  nextTick(() => {
    if (open) {
      setTimeout(() => {
        get(input)?.focus?.();
      }, 100);
    }
    set(selected, undefined);
    set(search, '');
  });
});

function change(index?: number) {
  if (!index)
    return;

  const item: SearchItem = get(visibleItems)[index];
  if (item) {
    if (item.route && get(router.currentRoute).fullPath !== item.route)
      startPromise(router.push(item.route));

    item?.action?.();
    set(open, false);
  }
}

const interop = useInterop();
onBeforeMount(async () => {
  set(isMac, await interop.isMac());

  window.addEventListener('keydown', (event) => {
    // Mac use Command, Others use Control
    if (((get(isMac) && event.metaKey) || (!get(isMac) && event.ctrlKey)) && event.key === key)
      set(open, true);
  });
});
</script>

<template>
  <RuiDialog
    v-model="open"
    max-width="800"
    content-class="mt-[16rem] !top-0 pb-2"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="
          t('global_search.menu_tooltip', {
            modifier,
            key,
          })
        "
        v-bind="attrs"
      >
        <RuiIcon name="search-line" />
      </MenuTooltipButton>
    </template>
    <RuiCard
      variant="flat"
      no-padding
      rounded="sm"
      class="[&>div:last-child]:overflow-hidden"
    >
      <RuiAutoComplete
        ref="input"
        v-model="selected"
        v-model:search-input="search"
        no-filter
        :no-data-text="t('global_search.no_actions')"
        hide-details
        :loading="loading"
        :item-height="50"
        :options="visibleItems"
        text-attr="text"
        key-attr="value"
        label=""
        auto-select-first
        :placeholder="t('global_search.search_placeholder')"
        @update:model-value="change($event)"
      >
        <template #selection>
          <span />
        </template>
        <template #item="{ item }">
          <div class="flex items-center text-body-2 w-full">
            <AssetIcon
              v-if="item.asset"
              class="-my-1"
              size="30px"
              :identifier="item.asset"
            />
            <template v-else>
              <LocationIcon
                v-if="item.location"
                icon
                size="26px"
                :item="item.location.identifier"
              />
              <AppImage
                v-else-if="item.image"
                class="icon-bg"
                :src="item.image"
                contain
                size="26px"
              />
              <RuiIcon
                v-else-if="item.icon"
                :name="item.icon"
                size="26px"
              />
            </template>
            <div class="ml-3 flex items-center">
              <template v-if="item.texts">
                <div
                  v-for="(text, index) in item.texts"
                  :key="text + index"
                  class="flex items-center"
                >
                  <div v-if="index === item.texts.length - 1">
                    {{ text }}
                  </div>
                  <div
                    v-else
                    class="flex items-center text-rui-text-secondary"
                  >
                    {{ text }}
                    <RuiIcon
                      class="d-inline mx-2"
                      size="16"
                      name="arrow-right-s-line"
                    />
                  </div>
                </div>
              </template>
              <template v-else>
                {{ item.text }}
              </template>
            </div>
            <div class="grow" />
            <div
              v-if="item.price"
              class="text-right -my-6"
            >
              <div class="text-caption">
                {{ t('common.price') }}:
              </div>
              <AmountDisplay
                class="font-bold"
                :fiat-currency="currencySymbol"
                :value="item.price"
              />
            </div>
            <div
              v-if="item.total"
              class="text-right -my-4"
            >
              <div class="text-caption">
                {{ t('common.total') }}:
              </div>
              <AmountDisplay
                class="font-bold"
                :fiat-currency="currencySymbol"
                :value="item.total"
              />
            </div>
          </div>
        </template>
      </RuiAutoComplete>
    </RuiCard>
  </RuiDialog>
</template>
