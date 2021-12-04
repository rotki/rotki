<template>
  <import-source source="gitcoin">
    <span>{{ $t('import_data.gitcoin.description') }}</span>
  </import-source>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import ImportSource from '@/components/import/ImportSource.vue';

export default defineComponent({
  name: 'GitcoinImport',
  components: { ImportSource }
});
</script>
