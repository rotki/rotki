<template>
  <v-container>
    <card-title class="mt-2">{{ $t('import_data.title') }}</card-title>
    <v-row class="mt-4" no-gutters>
      <v-col cols="12">
        {{ $t('import_data.description') }}
      </v-col>
      <v-col cols="12">
        <v-alert outlined class="mt-2">
          <i18n tag="span" path="import_data.notice">
            <template #warning>
              <strong> {{ $t('import_data.notice_warning') }}</strong>
            </template>
            <template #link>
              <external-link
                url="https://github.com/rotki/rotki/issues/new/choose"
              >
                {{ $t('import_data.notice_link') }}
              </external-link>
            </template>
          </i18n>
        </v-alert>
      </v-col>
    </v-row>
    <cointracking-import class="mt-8" />
    <crypto-com-import class="mt-8" />
    <block-fi-import class="mt-8" />
    <nexo-import class="mt-8" />
    <shapeshift-import class="mt-8" />
    <uphold-import class="mt-8"/>
    <import-source
      v-if="premium"
      class="mt-8"
      source="gitcoin"
      :icon="require('@/assets/images/import/gitcoin.svg')"
    >
      <span>{{ $t('import_data.gitcoin.description') }}</span>
    </import-source>
  </v-container>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import BlockFiImport from '@/components/import/BlockFiImport.vue';
import CointrackingImport from '@/components/import/CointrackingImport.vue';
import CryptoComImport from '@/components/import/CryptoComImport.vue';
import ImportSource from '@/components/import/ImportSource.vue';
import NexoImport from '@/components/import/NexoImport.vue';
import ShapeshiftImport from '@/components/import/ShapeshiftImport.vue';
import UpholdImport from '@/components/import/UpholdImport.vue';
import PremiumMixin from '@/mixins/premium-mixin';

export default defineComponent({
  components: {
    UpholdImport,
    ShapeshiftImport,
    NexoImport,
    BlockFiImport,
    CryptoComImport,
    CointrackingImport,
    ImportSource,
    ExternalLink
  },
  mixins: [PremiumMixin]
});
</script>
