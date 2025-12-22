<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';

const props = defineProps<{
  code: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const mccIconMap: Record<string, RuiIcons> = {
  4121: 'lu-car', // Taxicabs and Rideshares
  5200: 'lu-hammer', // Home Supply Warehouse Stores
  5310: 'lu-percent', // Discount Stores
  5311: 'lu-store', // Department Stores
  5331: 'lu-coins', // Variety Stores (Dollar Stores)
  5411: 'lu-shopping-cart', // Grocery Stores, Supermarkets
  5462: 'lu-croissant', // Bakeries
  5541: 'lu-fuel', // Service Stations (Gas Stations)
  5621: 'lu-shopping-bag', // Women's Ready-to-Wear Stores
  5651: 'lu-users', // Family Clothing Stores
  5691: 'lu-shirt', // Clothing Stores
  5732: 'lu-smartphone', // Electronics Stores
  5812: 'lu-utensils', // Eating Places, Restaurants
  5813: 'lu-wine', // Bars, Cocktail Lounges, Taverns
  5814: 'lu-hamburger', // Fast Food Restaurants
  5912: 'lu-pill', // Drug Stores, Pharmacies
  5942: 'lu-book-open', // Book Stores
  5977: 'lu-sparkles', // Cosmetic Stores
  5999: 'lu-shopping-bag', // Miscellaneous Retail Stores
  7011: 'lu-bed', // Hotels, Motels, Resorts
};

const DEFAULT_ICON = 'lu-store';

const iconName = computed<string>(() => mccIconMap[props.code] ?? DEFAULT_ICON);
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <span class="size-5 inline-flex items-center justify-center rounded-full bg-rui-primary text-white transform translate-y-0.5">
        <RuiIcon
          v-if="code"
          :name="iconName"
          size="14"
          class="inline"
        />
      </span>
    </template>
    {{ t('transactions.events.note.merchant_code', { code }) }}
  </RuiTooltip>
</template>
