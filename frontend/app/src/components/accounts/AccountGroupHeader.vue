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
        '!p-2': !xs
      }"
    >
      <div class="pl-9">
        <span class="text-subtitle-2">{{ label }}</span>
      </div>
      <div class="flex items-center gap-1 -my-2">
        <RuiButton
          :disabled="items.length === 0"
          variant="text"
          size="sm"
          icon
          @click="expandClicked({ ...xpub, balance })"
        >
          <RuiIcon v-if="expanded" name="arrow-up-s-line" />
          <RuiIcon v-else name="arrow-down-s-line" />
        </RuiButton>
        <span class="font-medium">
          {{ t('account_group_header.xpub') }}
        </span>
        <span :class="{ blur: !shouldShowAmount }">
          <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
            <template #activator>
              {{ displayXpub }}
            </template>
            {{ xpub.xpub }}
          </RuiTooltip>
        </span>
        <CopyButton
          :value="xpub.xpub"
          :tooltip="t('account_group_header.copy_tooltip')"
        />
        <span v-if="xpub.derivationPath" :class="{ blur: !shouldShowAmount }">
          <span class="font-medium">
            {{ t('account_group_header.derivation_path') }}:
          </span>
          {{ xpub.derivationPath }}
        </span>
      </div>
      <TagDisplay wrapper-class="ml-9" :tags="xpubTags" />
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
      <RowActions
        :edit-tooltip="t('account_group_header.edit_tooltip')"
        :delete-tooltip="t('account_group_header.delete_tooltip')"
        @edit-click="editClicked(xpub)"
        @delete-click="deleteClicked(xpub)"
      />
    </td>
  </Fragment>
</template>
