<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import DataIssuesView from '@/modules/history/data-issues/DataIssuesView.vue';
import ReconciliationView from '@/modules/history/reconciliation/ReconciliationView.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.history_sub.data_issues'), icon: 'lu-shield-alert', parent: '/history/', order: 20, drawer: 'history-data-issues' },
    canNavigateBack: true,
    noteLocation: NoteLocation.HISTORY,
  },
  props: true,
});

const { tab } = defineProps<{
  tab?: string;
}>();

const router = useRouter();
const route = useRoute();

const isReconciliation = computed<boolean>(() => tab === 'reconciliation');

/**
 * Sends bare and unknown tab URLs to the issues tab.
 *
 * @remarks
 * `/history/data-issues` is the pre-tab URL and must keep opening the issues list. An unknown
 * segment is treated the same way rather than rendering an empty page.
 */
watchImmediate(route, () => {
  const current = route.params.tab;
  if (current === 'reconciliation' || current === 'issues')
    return;

  startPromise(router.replace({
    name: '/history/data-issues/[[tab]]',
    params: { tab: 'issues' },
    query: route.query,
  }));
}, { deep: true });
</script>

<template>
  <ReconciliationView v-if="isReconciliation" />
  <DataIssuesView
    v-else
    main-page
  />
</template>
