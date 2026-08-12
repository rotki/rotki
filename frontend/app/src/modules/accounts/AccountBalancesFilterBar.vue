<script setup lang="ts">
import type { SavedViewState } from '@/modules/core/table/pill/composables/use-saved-views';
import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import { useBlockchainAccountFields } from '@/modules/accounts/use-blockchain-account-fields';
import { arrayify } from '@/modules/core/common/data/array';
import { SavedFilterLocations } from '@/modules/core/table/filtering';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import PillViewsMenu from '@/modules/core/table/pill/PillViewsMenu.vue';

const visibleTags = defineModel<string[]>('visibleTags', { required: true });
const addresses = defineModel<string[]>('addresses', { required: true });
const chains = defineModel<string[]>('chains', { required: true });

const { category } = defineProps<{
  category: string;
}>();

const fields = useBlockchainAccountFields(() => category);
const pillLabels = usePillBarLabels();

// Every pill in this bar is param-bound (paramKeys `addresses`, `chain`, `tags`).
// Bridge the bar's param bag to the models backing them, so the bar drives the same sources the
// standalone selectors used to. An absent param clears its model: removing the pill is how the
// filter is turned off.
function toList(value: string | string[] | boolean | undefined): string[] {
  return value === undefined || typeof value === 'boolean' ? [] : arrayify(value);
}

const pillParams = computed<Record<string, string | string[] | boolean>>({
  get(): Record<string, string | string[] | boolean> {
    const tags = get(visibleTags);
    const picked = get(addresses);
    const chain = get(chains);
    return {
      ...(picked.length > 0 ? { addresses: picked } : {}),
      ...(chain.length > 0 ? { chain } : {}),
      ...(tags.length > 0 ? { tags } : {}),
    };
  },
  set(value: Record<string, string | string[] | boolean>): void {
    set(addresses, toList(value.addresses));
    set(chains, toList(value.chain));
    set(visibleTags, toList(value.tags));
  },
});

// A saved view is the bar's two models under a name, so it both reads from and writes to the same
// pair the bar is bound to.
// Every pill here is param-bound, so a view is its params alone. `matches` stays in the stored
// shape because it is the bar's own serialized form, shared with the tables that do have matchers.
const pillState = computed<SavedViewState>(() => ({
  matches: {},
  params: get(pillParams),
}));

function applyView(view: SavedView): void {
  set(pillParams, view.params);
}
</script>

<template>
  <PillFilterBar
    v-model:params="pillParams"
    class="flex-1 min-w-[12rem] md:min-w-[24rem]"
    :fields="fields"
    :labels="pillLabels"
  >
    <template #views="{ disabled }">
      <PillViewsMenu
        :fields="fields"
        :location="SavedFilterLocations.BLOCKCHAIN_ACCOUNTS"
        :state="pillState"
        :disabled="disabled"
        @apply="applyView($event)"
      />
    </template>
  </PillFilterBar>
</template>
