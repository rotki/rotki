<template>
  <card outlined-body>
    <template #title>
      {{ $t('kraken_staking_events.titles') }}
      <v-icon v-if="loading" color="primary" class="ml-2">
        mdi-spin mdi-loading
      </v-icon>
    </template>
    <template #actions>
      <v-row class="font-weight-medium">
        <v-col>{{ $t('kraken_staking_events.filter_title') }}</v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="auto" class="flex-grow-1">
          <date-time-picker
            ref="startField"
            v-model="start"
            outlined
            allow-empty
            seconds
            :label="$t('kraken_staking_events.filter.from')"
          />
        </v-col>
        <v-col cols="12" md="auto" class="flex-grow-1">
          <date-time-picker
            ref="endField"
            v-model="end"
            outlined
            limit-now
            allow-empty
            seconds
            :label="$t('kraken_staking_events.filter.to')"
          />
        </v-col>
        <v-col cols="auto">
          <v-btn
            depressed
            primary
            :class="{
              'mt-3': !isMobile
            }"
            @click="clear"
          >
            {{ $t('kraken_staking_events.clear') }}
          </v-btn>
        </v-col>
      </v-row>
    </template>
    <data-table :items="events" :headers="headers" sort-by="timestamp">
      <template #item.eventType="{ item }">
        {{ item.eventType }}
      </template>
      <template #item.asset="{ item }">
        <asset-details :asset="item.asset" />
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display :value="item.usdValue" />
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  unref,
  watch
} from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import { setupThemeCheck } from '@/composables/common';
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import {
  KrakenStakingEvents,
  KrakenStakingPagination,
  KrakenStakingPaginationOptions
} from '@/types/staking';
import { convertToTimestamp } from '@/utils/date';

const getHeaders = (): DataTableHeader[] => [
  {
    text: i18n.t('kraken_staking_events.column.event_type').toString(),
    value: 'eventType'
  },
  {
    text: i18n.t('kraken_staking_events.column.asset').toString(),
    value: 'asset'
  },
  {
    text: i18n.t('kraken_staking_events.column.time').toString(),
    value: 'timestamp'
  },
  {
    text: i18n.t('kraken_staking_events.column.amount').toString(),
    value: 'amount',
    align: 'end'
  },
  {
    text: i18n.t('kraken_staking_events.column.value').toString(),
    value: 'usdValue',
    align: 'end'
  }
];

export default defineComponent({
  name: 'KrakenStakingEvents',
  props: {
    events: {
      required: true,
      type: Array as PropType<KrakenStakingEvents>
    },
    loading: {
      required: false,
      type: Boolean,
      default: false
    }
  },
  emit: ['update:pagination'],
  setup(_, { emit }) {
    const start = ref('');
    const end = ref('');
    const startField = ref();
    const endField = ref();

    const { itemsPerPage, dateInputFormat } = setupSettings();
    const { isMobile } = setupThemeCheck();

    const options = ref<KrakenStakingPaginationOptions>({
      page: 1,
      itemsPerPage: unref(itemsPerPage),
      sortBy: ['timestamp'],
      sortDesc: [true]
    });

    const fromTimestamp = computed(() => {
      const from = unref(start);
      if (!from) {
        return undefined;
      }
      return convertToTimestamp(from, dateInputFormat.value);
    });

    const toTimestamp = computed(() => {
      const to = unref(end);
      if (!to) {
        return undefined;
      }
      return convertToTimestamp(to, dateInputFormat.value);
    });

    const updatePagination = (
      { itemsPerPage, page, sortBy, sortDesc }: KrakenStakingPaginationOptions,
      fromTimestamp?: number,
      toTimestamp?: number
    ) => {
      const pagination: KrakenStakingPagination = {
        ascending: sortDesc[0],
        orderByAttribute: sortBy[0],
        limit: itemsPerPage,
        offset: (page - 1) * itemsPerPage,
        fromTimestamp,
        toTimestamp
      };
      emit('update:pagination', pagination);
    };

    const clear = () => {
      start.value = '';
      end.value = '';
      unref(startField)?.reset();
      unref(endField)?.reset();
    };

    watch(options, options =>
      updatePagination(options, unref(fromTimestamp), unref(toTimestamp.value))
    );
    watch([fromTimestamp, toTimestamp], ([from, to]) =>
      updatePagination(unref(options), from, to)
    );

    return {
      start,
      end,
      startField,
      endField,
      options,
      isMobile,
      headers: getHeaders(),
      clear
    };
  }
});
</script>
