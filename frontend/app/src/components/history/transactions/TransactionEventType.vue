<template>
  <div class="d-flex align-center text-left">
    <v-badge v-if="counterparty" avatar overlap color="white">
      <template #badge>
        <v-tooltip top>
          <template #activator="{ on }">
            <div v-on="on">
              <v-avatar>
                <v-icon v-if="counterparty.icon" :color="counterparty.color">
                  {{ counterparty.icon }}
                </v-icon>
                <v-img v-else :src="counterparty.image" />
              </v-avatar>
            </div>
          </template>
          <div>{{ counterparty.label }}</div>
        </v-tooltip>
      </template>
      <v-avatar
        class="text--darken-4"
        :color="dark ? 'white' : 'grey lighten-3'"
        :size="36"
      >
        <v-icon :size="20" :color="attrs.color || 'grey darken-2'">
          {{ attrs.icon }}
        </v-icon>
      </v-avatar>
    </v-badge>
    <v-avatar
      v-else
      class="text--darken-4"
      :color="dark ? 'white' : 'grey lighten-3'"
      :size="36"
    >
      <v-icon :size="20" :color="attrs.color || 'grey darken-2'">
        {{ attrs.icon }}
      </v-icon>
    </v-avatar>
    <div class="ml-4">
      <div class="font-weight-bold text-uppercase">{{ attrs.label }}</div>
      <div v-if="event.locationLabel" class="grey--text">
        <hash-link :text="event.locationLabel" />
      </div>
      <div v-if="event.customized" class="pt-1">
        <v-chip small label color="primary accent-1">
          <v-icon x-small> mdi-file-document-edit </v-icon>
          <div class="pl-2 text-caption font-weight-bold">
            {{ t('transactions.events.customized_event') }}
          </div>
        </v-chip>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { PropType } from 'vue';
import { useTheme } from '@/composables/common';
import { EthTransactionEventEntry } from '@/store/history/types';
import { ActionDataEntry } from '@/store/types';
import { getEventCounterpartyData, useEventTypeData } from '@/utils/history';

const props = defineProps({
  event: {
    required: true,
    type: Object as PropType<EthTransactionEventEntry>
  }
});

const { event } = toRefs(props);

const { dark } = useTheme();
const { getEventTypeData } = useEventTypeData();

const attrs = computed<ActionDataEntry>(() => {
  return getEventTypeData(get(event));
});

const counterparty = computed<ActionDataEntry | null>(() => {
  return getEventCounterpartyData(get(event));
});

const { t } = useI18n();
</script>
