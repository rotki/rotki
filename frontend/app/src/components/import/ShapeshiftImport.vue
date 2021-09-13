<template>
  <import-source source="shapeshift-trades">
    <template #image>
      <shape-shift-horizontal />
    </template>
    <template #upload-title>
      <i18n tag="span" path="import_data.shapeshift.import">
        <strong>{{ $t('import_data.shapeshift.import_trade') }}</strong>
      </i18n>
    </template>
    <i18n tag="span" path="import_data.shapeshift.note">
      <strong>{{ $t('import_data.shapeshift.name') }}</strong>
    </i18n>
    <ul>
      <li>{{ $t('import_data.shapeshift.line_one') }}</li>
      <li>{{ $t('import_data.shapeshift.line_two') }}</li>
    </ul>
  </import-source>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import ShapeShiftHorizontal from '@/components/images/ShapeShiftHorizontal.vue';
import ImportSource from '@/components/import/ImportSource.vue';

export default defineComponent({
  name: 'ShapeshiftImport',
  components: { ImportSource, ShapeShiftHorizontal }
});
</script>
