<template>
  <v-tooltip top open-delay="400">
    <template #activator="{ on, attrs }">
      <v-icon v-if="nameMode" v-bind="attrs" v-on="on" @click="updateMode">
        mdi-form-textbox
      </v-icon>
      <v-icon v-else v-bind="attrs" v-on="on" @click="updateMode">
        mdi-symbol
      </v-icon>
    </template>
    <span v-if="nameMode">
      {{ $t('asset_filter_mode_indicator.name_mode_hint') }}
    </span>
    <span v-else>
      {{ $t('asset_filter_mode_indicator.symbol_mode_hint') }}
    </span>
  </v-tooltip>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({
  name: 'AssetFilterModeIndicator'
})
export default class AssetFilterModeIndicator extends Vue {
  @Prop({ required: true, type: Boolean })
  nameMode!: boolean;
  @Emit('mode:update')
  updateMode() {}
}
</script>
<style scoped lang="scss"></style>
