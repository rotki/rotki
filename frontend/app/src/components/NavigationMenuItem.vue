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
          <v-img
            v-else-if="image"
            contain
            width="24px"
            :src="image"
            class="nav-icon"
            :class="$style.icon"
          />
          <component
            :is="iconComponent"
            v-else-if="iconComponent"
            :active="active"
          />
          <v-icon v-else>{{ icon }}</v-icon>
        </v-list-item-icon>
      </template>
      <span>{{ text }}</span>
    </v-tooltip>
    <v-list-item-icon v-else>
      <asset-icon v-if="!!cryptoIcon" :identifier="identifier" size="24px" />
      <v-img
        v-else-if="image"
        contain
        width="24px"
        :src="image"
        class="nav-icon"
        :class="$style.icon"
      />
      <component
        :is="iconComponent"
        v-else-if="iconComponent"
        :active="active"
      />
      <v-icon v-else>{{ icon }}</v-icon>
    </v-list-item-icon>
    <v-list-item-content class="d-flex flex-grow-1">
      <v-list-item-title>{{ text }}</v-list-item-title>
    </v-list-item-content>
  </div>
</template>

<script lang="ts">
import { VueConstructor } from 'vue';
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
  @Prop({ required: false })
  image!: string;
  @Prop({ required: false })
  iconComponent!: VueConstructor | undefined;
  @Prop({ required: false, type: Boolean, default: false })
  active!: boolean;

  getIdentifierForSymbol!: IdentifierForSymbolGetter;

  get identifier(): string {
    return this.getIdentifierForSymbol(this.cryptoIcon) ?? this.cryptoIcon;
  }
}
</script>

<style module lang="scss">
.icon {
  opacity: 0.66;
}
</style>
