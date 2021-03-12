<template>
  <v-tooltip v-if="canNavigateBack" open-delay="400" top>
    <template #activator="{ on, attrs }">
      <v-btn
        icon
        class="back-button__button"
        v-bind="attrs"
        v-on="on"
        @click="goBack()"
      >
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
    </template>
    <span>{{ $t('back_button.tooltip') }}</span>
  </v-tooltip>
  <div v-else class="back-button__placeholder" />
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class BackButton extends Vue {
  @Prop({ required: true, default: false, type: Boolean })
  canNavigateBack!: boolean;

  goBack() {
    this.$router.go(-1);
  }
}
</script>
<style scoped lang="scss">
.back-button {
  &__button,
  &__placeholder {
    margin-left: 24px;
    width: 48px;
  }
}
</style>
