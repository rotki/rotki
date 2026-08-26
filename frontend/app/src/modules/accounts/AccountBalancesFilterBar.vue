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

/**
 * Normalizes a param value to the list its model expects.
 *
 * @returns an empty list for an absent param, which is how removing a pill clears its filter.
 */
function toList(value: string | string[] | boolean | undefined): string[] {
  return value === undefined || typeof value === 'boolean' ? [] : arrayify(value);
}

/**
 * The bar's param bag, bridged to the models behind each pill.
 *
 * @remarks
 * Every pill here is param-bound (`addresses`, `chain`, `tags`), so the bar drives these models
 * and nothing else does. Writing an absent param clears its model rather than leaving the previous
 * value in place, since removing a pill is how the user turns that filter off.
 */
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

/**
 * A saved view: the bar's models under a name, read and written through the same pair.
 *
 * @remarks
 * Every pill here is param-bound, so a view is its params alone and `matches` is always empty. The
 * key is kept in the stored shape regardless, because that shape is shared with the tables that do
 * have matchers.
 */
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
