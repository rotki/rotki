<script lang="ts" setup>
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { KrakenStakingDateFilter } from '@/modules/staking/staking-types';
import { assert } from '@rotki/common';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { KrakenStakingFilterValueKeys, useKrakenStakingFields } from '@/modules/staking/kraken/use-kraken-staking-fields';

const modelValue = defineModel<KrakenStakingDateFilter>({ required: true });

const fields = useKrakenStakingFields();
const pillLabels = usePillBarLabels();

/**
 * The bar's model is the flat keyword map every table filter speaks; this page's model is the
 * `{ fromTimestamp, toTimestamp }` object it hands to `fetchEvents` and to the events table below.
 * The bridge is the whole reason this component exists.
 */
const matches = computed<MatchedKeywordWithBehaviour<string>>({
  get() {
    const model = get(modelValue);
    return {
      ...(model.fromTimestamp ? { [KrakenStakingFilterValueKeys.START]: model.fromTimestamp.toString() } : {}),
      ...(model.toTimestamp ? { [KrakenStakingFilterValueKeys.END]: model.toTimestamp.toString() } : {}),
    };
  },
  set(value) {
    const fromTimestamp = value[KrakenStakingFilterValueKeys.START];
    const toTimestamp = value[KrakenStakingFilterValueKeys.END];
    assert(typeof fromTimestamp === 'string' || fromTimestamp === undefined);
    assert(typeof toTimestamp === 'string' || toTimestamp === undefined);

    set(modelValue, {
      fromTimestamp: fromTimestamp ? Number(fromTimestamp) : undefined,
      toTimestamp: toTimestamp ? Number(toTimestamp) : undefined,
    });
  },
});
</script>

<template>
  <!--
    The bar draws a border but no surface of its own: everywhere else it sits inside a card, which
    is what makes it read as a white input. Here it sits straight on the page background, so it
    brings the surface its own pills already assume.
  -->
  <PillFilterBar
    v-model:matches="matches"
    class="bg-white dark:bg-rui-grey-900"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
