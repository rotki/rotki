<template>
  <td v-if="!group" class="font-weight-medium" colspan="5" :class="mobileClass">
    {{ tc('account_group_header.standalone') }}
  </td>
  <fragment v-else>
    <td
      :colspan="xsOnly ? 1 : 2"
      :class="{
        'v-data-table__mobile-row': xsOnly,
        'pa-2': !xsOnly
      }"
    >
      <div class="ps-8">
        <span class="text-subtitle-2">{{ label }}</span>
      </div>
      <div>
        <v-btn
          v-if="items.length > 0"
          small
          icon
          @click="expandClicked({ ...xpub, balance })"
        >
          <v-icon v-if="expanded" small>mdi-chevron-up</v-icon>
          <v-icon v-else small>mdi-chevron-down</v-icon>
        </v-btn>
        <v-btn v-else small icon disabled />
        <span class="font-weight-medium">
          {{ tc('account_group_header.xpub') }}
        </span>
        <span :class="{ 'blur-content': !shouldShowAmount }">
          <v-tooltip top open-delay="400">
            <template #activator="{ on }">
              <span v-on="on">{{ displayXpub }}</span>
            </template>
            <span> {{ xpub.xpub }} </span>
          </v-tooltip>
        </span>
        <copy-button
          :value="xpub.xpub"
          :tooltip="tc('account_group_header.copy_tooltip')"
        />
        <span
          v-if="xpub.derivationPath"
          :class="{ 'blur-content': !shouldShowAmount }"
        >
          <span class="font-weight-medium">
            {{ tc('account_group_header.derivation_path') }}
          </span>
          {{ xpub.derivationPath }}
        </span>
      </div>
      <tag-display
        v-if="xpubTags && xpubTags.length > 0"
        wrapper-class="mt-1 ms-8"
        :tags="xpubTags"
      />
    </td>
    <td class="text-end" :class="mobileClass">
      <amount-display
        :value="sum"
        :loading="loading"
        :asset="xsOnly ? 'BTC' : null"
      />
    </td>
    <td class="text-end" :class="mobileClass">
      <amount-display
        fiat-currency="USD"
        show-currency="symbol"
        :value="usdSum"
        :loading="loading"
      />
    </td>
    <td class="text-end" :class="mobileClass">
      <div class="d-flex">
        <v-tooltip top>
          <template #activator="{ on, attrs }">
            <v-btn
              v-bind="attrs"
              icon
              :disabled="false"
              class="mx-1"
              v-on="on"
              @click="editClicked(xpub)"
            >
              <v-icon small> mdi-pencil-outline </v-icon>
            </v-btn>
          </template>
          <span>{{ tc('account_group_header.edit_tooltip') }}</span>
        </v-tooltip>
        <v-tooltip top open-delay="400">
          <template #activator="{ on }">
            <v-btn icon class="mr-1" v-on="on" @click="deleteClicked(xpub)">
              <v-icon small>mdi-delete-outline</v-icon>
            </v-btn>
          </template>
          <span> {{ tc('account_group_header.delete_tooltip') }} </span>
        </v-tooltip>
      </div>
    </td>
  </fragment>
</template>
<script setup lang="ts">
import { Balance, BigNumber } from '@rotki/common';
import { PropType } from 'vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import Fragment from '@/components/helper/Fragment';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useTheme } from '@/composables/common';
import { bigNumberSum, truncateAddress, truncationPoints } from '@/filters';
import { XpubAccountWithBalance } from '@/store/balances/types';
import { balanceUsdValueSum } from '@/store/defi/utils';
import { useSessionSettingsStore } from '@/store/settings/session';

const props = defineProps({
  group: { required: true, type: String },
  items: {
    required: true,
    type: Array as PropType<XpubAccountWithBalance[]>
  },
  expanded: { required: true, type: Boolean },
  loading: { required: false, type: Boolean, default: false }
});

const emit = defineEmits(['delete-clicked', 'expand-clicked', 'edit-clicked']);

const { items } = toRefs(props);
const { breakpoint, currentBreakpoint } = useTheme();
const xsOnly = computed(() => get(currentBreakpoint).xsOnly);
const { shouldShowAmount } = storeToRefs(useSessionSettingsStore());

const mobileClass = computed<string | null>(() => {
  return get(xsOnly) ? 'v-data-table__mobile-row' : null;
});

const xpub = computed<XpubAccountWithBalance>(() => {
  return get(items).filter(item => !item.address)[0];
});

const label = computed<string>(() => {
  return get(xpub).label;
});

const xpubTags = computed<string[]>(() => {
  return get(xpub).tags;
});

const displayXpub = computed<string>(() => {
  return truncateAddress(
    get(xpub).xpub,
    truncationPoints[get(breakpoint)] ?? 4
  );
});

const sum = computed<BigNumber>(() => {
  return bigNumberSum(get(items).map(({ balance: { amount } }) => amount));
});

const usdSum = computed<BigNumber>(() => {
  return balanceUsdValueSum(get(items));
});

const balance = computed<Balance>(() => {
  return {
    amount: get(sum),
    usdValue: get(usdSum)
  };
});

const deleteClicked = (_payload: XpubAccountWithBalance) =>
  emit('delete-clicked', _payload);

const expandClicked = (_payload: XpubAccountWithBalance) =>
  emit('expand-clicked', _payload);

const editClicked = (_payload: XpubAccountWithBalance) =>
  emit('edit-clicked', _payload);

const { tc } = useI18n();
</script>
<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}
</style>
