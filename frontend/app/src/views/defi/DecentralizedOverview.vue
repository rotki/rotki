<template>
  <div>
    <v-row class="mt-6">
      <v-col>
        <refresh-header
          :loading="refreshing"
          :title="$t('decentralized_overview.title')"
          @refresh="refresh()"
        />
      </v-col>
    </v-row>
    <progress-screen v-if="loading">
      <template #message>{{ $t('decentralized_overview.loading') }}</template>
    </progress-screen>
    <no-data-screen
      v-else-if="overview.length === 0"
      :full="false"
      class="mt-16"
    >
      <template #title>
        {{ $t('decentralized_overview.empty_title') }}
      </template>
      <span class="text-subtitle-2 text--secondary">
        {{ $t('decentralized_overview.empty_subtitle') }}
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

<script lang="ts">
import { defineComponent, onMounted } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import NoDataScreen from '@/components/common/NoDataScreen.vue';
import Overview from '@/components/defi/Overview.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import { setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useDefiStore } from '@/store/defi';

export default defineComponent({
  name: 'DecentralizedOverview',
  components: {
    NoDataScreen,
    ProgressScreen,
    Overview,
    RefreshHeader
  },
  setup() {
    const store = useDefiStore();
    const { overview } = storeToRefs(store);
    const section = Section.DEFI_OVERVIEW;

    const refresh = async () => {
      await store.fetchAllDefi(true);
    };

    onMounted(async () => {
      await store.fetchAllDefi(false);
    });

    const { shouldShowLoadingScreen, isSectionRefreshing } =
      setupStatusChecking();

    return {
      overview,
      loading: shouldShowLoadingScreen(section),
      refreshing: isSectionRefreshing(section),
      refresh
    };
  }
});
</script>
