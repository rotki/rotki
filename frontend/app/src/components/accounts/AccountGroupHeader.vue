<script setup lang="ts">
import { type Balance, type BigNumber } from '@rotki/common';
import { type ComputedRef } from 'vue';
import Fragment from '@/components/helper/Fragment';
import { type XpubAccountWithBalance } from '@/types/blockchain/accounts';

const props = withDefaults(
  defineProps<{
    group: string;
    items: XpubAccountWithBalance[];
    expanded: boolean;
    loading?: boolean;
  }>(),
  { loading: false }
);

const emit = defineEmits(['delete-clicked', 'expand-clicked', 'edit-clicked']);

const { t } = useI18n();

const { items } = toRefs(props);
const { name: breakpoint, xs } = useDisplay();
const { shouldShowAmount } = storeToRefs(useSessionSettingsStore());

const mobileClass = computed<string | null>(() =>
  get(xs) ? 'v-data-table__mobile-row' : null
);

const xpub: ComputedRef<XpubAccountWithBalance> = computed(() => {
  const account = get(items).find(item => !item.address);
  assert(account);
  return account;
});

const label = computed<string>(() => get(xpub).label);

const xpubTags = computed<string[]>(() => get(xpub).tags);

const displayXpub = computed<string>(() =>
  truncateAddress(get(xpub).xpub, truncationPoints[get(breakpoint)] ?? 4)
);

const sum = computed<BigNumber>(() =>
  bigNumberSum(get(items).map(({ balance: { amount } }) => amount))
);

const usdSum = computed<BigNumber>(() => balanceUsdValueSum(get(items)));

const balance = computed<Balance>(() => ({
  amount: get(sum),
  usdValue: get(usdSum)
}));

const deleteClicked = (_payload: XpubAccountWithBalance) =>
  emit('delete-clicked', _payload);

const expandClicked = (_payload: XpubAccountWithBalance) =>
  emit('expand-clicked', _payload);

const editClicked = (_payload: XpubAccountWithBalance) =>
  emit('edit-clicked', _payload);
</script>

<template>
  <td v-if="!group" class="font-medium" colspan="5" :class="mobileClass">
    {{ t('account_group_header.standalone') }}
  </td>
  <Fragment v-else>
    <td
      :colspan="xs ? 1 : 2"
      :class="{
        'v-data-table__mobile-row': xs,
        'pa-2': !xs
      }"
    >
      <div class="ps-8">
        <span class="text-subtitle-2">{{ label }}</span>
      </div>
      <div>
        <VBtn
          v-if="items.length > 0"
          small
          icon
          @click="expandClicked({ ...xpub, balance })"
        >
          <VIcon v-if="expanded" small>mdi-chevron-up</VIcon>
          <VIcon v-else small>mdi-chevron-down</VIcon>
        </VBtn>
        <VBtn v-else small icon disabled />
        <span class="font-medium">
          {{ t('account_group_header.xpub') }}
        </span>
        <span :class="{ 'blur-content': !shouldShowAmount }">
          <VTooltip top open-delay="400">
            <template #activator="{ on }">
              <span v-on="on">{{ displayXpub }}</span>
            </template>
            <span> {{ xpub.xpub }} </span>
          </VTooltip>
        </span>
        <CopyButton
          :value="xpub.xpub"
          :tooltip="t('account_group_header.copy_tooltip')"
        />
        <span
          v-if="xpub.derivationPath"
          :class="{ 'blur-content': !shouldShowAmount }"
        >
          <span class="font-medium">
            {{ t('account_group_header.derivation_path') }}
          </span>
          {{ xpub.derivationPath }}
        </span>
      </div>
      <TagDisplay
        v-if="xpubTags && xpubTags.length > 0"
        wrapper-class="mt-1 ms-8"
        :tags="xpubTags"
      />
    </td>
    <td class="text-end" :class="mobileClass">
      <AmountDisplay
        :value="sum"
        :loading="loading"
        :asset="xs ? 'BTC' : null"
      />
    </td>
    <td class="text-end" :class="mobileClass">
      <AmountDisplay
        fiat-currency="USD"
        show-currency="symbol"
        :value="usdSum"
        :loading="loading"
      />
    </td>
    <td class="text-end" :class="mobileClass">
      <div class="flex">
        <VTooltip top>
          <template #activator="{ on, attrs }">
            <VBtn
              v-bind="attrs"
              icon
              :disabled="false"
              class="mx-1"
              v-on="on"
              @click="editClicked(xpub)"
            >
              <VIcon small> mdi-pencil-outline </VIcon>
            </VBtn>
          </template>
          <span>{{ t('account_group_header.edit_tooltip') }}</span>
        </VTooltip>
        <VTooltip top open-delay="400">
          <template #activator="{ on }">
            <VBtn icon class="mr-1" v-on="on" @click="deleteClicked(xpub)">
              <VIcon small>mdi-delete-outline</VIcon>
            </VBtn>
          </template>
          <span> {{ t('account_group_header.delete_tooltip') }} </span>
        </VTooltip>
      </div>
    </td>
  </Fragment>
</template>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}
</style>
