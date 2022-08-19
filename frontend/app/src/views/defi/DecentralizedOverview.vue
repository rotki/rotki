<template>
  <div>
    <v-row class="mt-6">
      <v-col>
        <refresh-header
          :loading="refreshing"
          :title="tc('decentralized_overview.title')"
          @refresh="refresh()"
        />
      </v-col>
    </v-row>
    <progress-screen v-if="loading">
      <template #message>{{ tc('decentralized_overview.loading') }}</template>
    </progress-screen>
    <no-data-screen
      v-else-if="overview.length === 0"
      :full="false"
      class="mt-16"
    >
      <template #title>
        {{ tc('decentralized_overview.empty_title') }}
      </template>
      <span class="text-subtitle-2 text--secondary">
        {{ tc('decentralized_overview.empty_subtitle') }}
      </span>
    </no-data-screen>
    <v-row class="mt-4">
      <v-col
        v-for="summary in overview"
        :key="summary.protocol.name"
        lg="6"
        xl="3"
      >
        <overview :summary="summary" />
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import NoDataScreen from '@/components/common/NoDataScreen.vue';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import Overview from '@/components/defi/Overview.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import { setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useDefiStore } from '@/store/defi';

const store = useDefiStore();
const { overview } = storeToRefs(store);
const section = Section.DEFI_OVERVIEW;

const { tc } = useI18n();

const refresh = async () => {
  await store.fetchAllDefi(true);
};

onMounted(async () => {
  await store.fetchAllDefi(false);
});

const { shouldShowLoadingScreen, isSectionRefreshing } = setupStatusChecking();

const loading = shouldShowLoadingScreen(section);
const refreshing = isSectionRefreshing(section);
</script>
