<template>
  <menu-tooltip-button
    :tooltip="$t('help_sidebar.tooltip')"
    class-name="secondary--text text--lighten-2"
    @click="visibleUpdate(!visible)"
  >
    <v-icon :class="visible ? 'help--visible' : null"> mdi-help-circle </v-icon>
  </menu-tooltip-button>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

@Component({
  name: 'HelpIndicator',
  components: { MenuTooltipButton }
})
export default class HelpIndicator extends Vue {
  @Prop({ required: true, type: Boolean })
  visible!: boolean;

  @Emit('visible:update')
  visibleUpdate(_visible: boolean) {}
}
</script>

<style scoped lang="scss">
.help {
  &--visible {
    transform: rotate(-25deg);
  }
}
</style>
