<script setup lang="ts">
import {
  type EvmChainAndTxHash,
  type EvmHistoryEvent,
  type HistoryEventEntry
} from '@/types/history/events';
import { toEvmChainAndTxHash } from '@/utils/history';
import { isEvmEventRef } from '@/utils/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
  loading: boolean;
}>();

const { event } = toRefs(props);

const evmEvent = isEvmEventRef(event);

const { tc } = useI18n();

const emit = defineEmits<{
  (e: 'add-event', event: EvmHistoryEvent): void;
  (e: 'toggle-ignore', event: HistoryEventEntry): void;
  (e: 'redecode', data: EvmChainAndTxHash): void;
}>();

const addEvent = (event: EvmHistoryEvent) => emit('add-event', event);
const toggleIgnore = (event: HistoryEventEntry) => emit('toggle-ignore', event);
const redecode = (data: EvmChainAndTxHash) => emit('redecode', data);
</script>

<template>
  <div class="d-flex align-center">
    <v-menu
      v-if="evmEvent"
      transition="slide-y-transition"
      max-width="250px"
      min-width="200px"
      offset-y
    >
      <template #activator="{ on }">
        <v-btn class="ml-1" icon v-on="on">
          <v-icon>mdi-dots-vertical</v-icon>
        </v-btn>
      </template>
      <v-list>
        <v-list-item link @click="addEvent(evmEvent)">
          <v-list-item-icon class="mr-4">
            <v-icon>mdi-plus</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            {{ tc('transactions.actions.add_event') }}
          </v-list-item-content>
        </v-list-item>
        <v-list-item link @click="toggleIgnore(event)">
          <v-list-item-icon class="mr-4">
            <v-icon v-if="event.ignoredInAccounting"> mdi-eye </v-icon>
            <v-icon v-else> mdi-eye-off</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            {{
              event.ignoredInAccounting
                ? tc('transactions.unignore')
                : tc('transactions.ignore')
            }}
          </v-list-item-content>
        </v-list-item>
        <v-list-item
          link
          :disabled="loading"
          @click="redecode(toEvmChainAndTxHash(evmEvent))"
        >
          <v-list-item-icon class="mr-4">
            <v-icon>mdi-database-refresh</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            {{ tc('transactions.actions.redecode_events') }}
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-menu>
  </div>
</template>
