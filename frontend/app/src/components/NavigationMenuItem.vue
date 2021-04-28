<template>
  <div class="d-flex flex-grow-1">
    <v-tooltip v-if="showTooltips" right>
      <template #activator="{ on }">
        <v-list-item-icon v-on="on">
          <asset-icon
            v-if="!!cryptoIcon"
            :identifier="identifier"
            size="24px"
          />
          <v-icon v-else>{{ icon }}</v-icon>
        </v-list-item-icon>
      </template>
      <span>{{ text }}</span>
    </v-tooltip>
    <v-list-item-icon v-else>
      <asset-icon v-if="!!cryptoIcon" :identifier="identifier" size="24px" />
      <v-icon v-else>{{ icon }}</v-icon>
    </v-list-item-icon>
    <v-list-item-content class="d-flex flex-grow-1">
      <v-list-item-title>{{ text }}</v-list-item-title>
    </v-list-item-content>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import { IdentifierForSymbolGetter } from '@/store/balances/types';

@Component({
  computed: {
    ...mapGetters('balances', ['getIdentifierForSymbol'])
  }
})
export default class NavigationMenuItem extends Vue {
  @Prop({ required: false, type: Boolean, default: false })
  showTooltips!: boolean;
  @Prop({ required: false, type: String, default: '' })
  icon!: string;
  @Prop({ required: false, type: String, default: '' })
  cryptoIcon!: string;
  @Prop({ required: true, type: String })
  text!: string;

  getIdentifierForSymbol!: IdentifierForSymbolGetter;

  get identifier(): string {
    return this.getIdentifierForSymbol(this.cryptoIcon) ?? this.cryptoIcon;
  }
}
</script>

<style scoped lang="scss"></style>
