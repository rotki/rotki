<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';

const { code } = defineProps<{
  code: string;
}>();

const { t } = useI18n({ useScope: 'global' });

/** ISO 18245 merchant category codes, which are opaque numbers on the wire. */
const MerchantCategory = {
  BAKERIES: 5462,
  BARS: 5813,
  BOOK_STORES: 5942,
  CLOTHING_STORES: 5691,
  COSMETIC_STORES: 5977,
  DEPARTMENT_STORES: 5311,
  DISCOUNT_STORES: 5310,
  DRUG_STORES: 5912,
  ELECTRONICS_STORES: 5732,
  FAMILY_CLOTHING_STORES: 5651,
  FAST_FOOD_RESTAURANTS: 5814,
  GROCERY_STORES: 5411,
  HOME_SUPPLY_WAREHOUSE_STORES: 5200,
  HOTELS: 7011,
  MISCELLANEOUS_RETAIL_STORES: 5999,
  RESTAURANTS: 5812,
  SERVICE_STATIONS: 5541,
  TAXICABS_AND_RIDESHARES: 4121,
  VARIETY_STORES: 5331,
  WOMEN_READY_TO_WEAR_STORES: 5621,
} as const;

const mccIconMap: Record<string, RuiIcons> = {
  [MerchantCategory.BAKERIES]: 'lu-croissant',
  [MerchantCategory.BARS]: 'lu-wine',
  [MerchantCategory.BOOK_STORES]: 'lu-book-open',
  [MerchantCategory.CLOTHING_STORES]: 'lu-shirt',
  [MerchantCategory.COSMETIC_STORES]: 'lu-sparkles',
  [MerchantCategory.DEPARTMENT_STORES]: 'lu-store',
  [MerchantCategory.DISCOUNT_STORES]: 'lu-percent',
  [MerchantCategory.DRUG_STORES]: 'lu-pill',
  [MerchantCategory.ELECTRONICS_STORES]: 'lu-smartphone',
  [MerchantCategory.FAMILY_CLOTHING_STORES]: 'lu-users',
  [MerchantCategory.FAST_FOOD_RESTAURANTS]: 'lu-hamburger',
  [MerchantCategory.GROCERY_STORES]: 'lu-shopping-cart',
  [MerchantCategory.HOME_SUPPLY_WAREHOUSE_STORES]: 'lu-hammer',
  [MerchantCategory.HOTELS]: 'lu-bed',
  [MerchantCategory.MISCELLANEOUS_RETAIL_STORES]: 'lu-shopping-bag',
  [MerchantCategory.RESTAURANTS]: 'lu-utensils',
  [MerchantCategory.SERVICE_STATIONS]: 'lu-fuel',
  [MerchantCategory.TAXICABS_AND_RIDESHARES]: 'lu-car',
  [MerchantCategory.VARIETY_STORES]: 'lu-coins',
  [MerchantCategory.WOMEN_READY_TO_WEAR_STORES]: 'lu-shopping-bag',
};

const DEFAULT_ICON = 'lu-store';

const iconName = computed<string>(() => mccIconMap[code] ?? DEFAULT_ICON);
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'top' }"
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
