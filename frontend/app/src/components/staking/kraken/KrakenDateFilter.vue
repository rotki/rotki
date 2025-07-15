<script lang="ts" setup>
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import type { KrakenStakingDateFilter } from '@/types/staking';
import { assert } from '@rotki/common';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { dateDeserializer, dateSerializer, dateValidator } from '@/utils/assets';
import { getDateInputISOFormat } from '@/utils/date';

const modelValue = defineModel<KrakenStakingDateFilter>({ required: true });

const { t } = useI18n({ useScope: 'global' });
const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

enum KrakenStakingFilterKeys {
  START = 'start',
  END = 'end',
}

enum KrakenStakingFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
}

export type KrakenStakingMatcher = SearchMatcher<KrakenStakingFilterKeys, KrakenStakingFilterValueKeys>;

export type KrakenStakingFilters = MatchedKeyword<KrakenStakingFilterValueKeys>;

const matchers = computed<KrakenStakingMatcher[]>(() => [{
  description: t('common.filter.start_date'),
  deserializer: dateDeserializer(dateInputFormat),
  hint: t('common.filter.date_hint', {
    format: getDateInputISOFormat(get(dateInputFormat)),
  }),
  key: KrakenStakingFilterKeys.START,
  keyValue: KrakenStakingFilterValueKeys.START,
  serializer: dateSerializer(dateInputFormat),
  string: true,
  suggestions: () => [],
  validate: dateValidator(dateInputFormat),
}, {
  description: t('common.filter.end_date'),
  deserializer: dateDeserializer(dateInputFormat),
  hint: t('common.filter.date_hint', {
    format: getDateInputISOFormat(get(dateInputFormat)),
  }),
  key: KrakenStakingFilterKeys.END,
  keyValue: KrakenStakingFilterValueKeys.END,
  serializer: dateSerializer(dateInputFormat),
  string: true,
  suggestions: () => [],
  validate: dateValidator(dateInputFormat),
}]);

const matches = computed<KrakenStakingFilters>({
  get() {
    const model = get(modelValue);
    return {
      ...(model.fromTimestamp ? { fromTimestamp: model.fromTimestamp.toString() } : {}),
      ...(model.toTimestamp ? { toTimestamp: model.toTimestamp.toString() } : {}),
    };
  },
  set(value) {
    const { fromTimestamp, toTimestamp } = value;
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
  <TableFilter
    v-model:matches="matches"
    :matchers="matchers"
  />
</template>
