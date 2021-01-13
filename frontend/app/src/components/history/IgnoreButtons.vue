<template>
  <v-row no-gutters class="mb-4">
    <v-tooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <v-btn
          text
          v-bind="attrs"
          :disabled="disabled"
          outlined
          v-on="on"
          @click="ignore(true)"
        >
          {{ $t('ignore_buttons.ignore') }}
        </v-btn>
      </template>
      <span>{{ $t('ignore_buttons.ignore_tooltip') }}</span>
    </v-tooltip>
    <v-col cols="auto" />
    <v-col cols="auto">
      <v-tooltip top open-delay="400">
        <template #activator="{ on, attrs }">
          <v-btn
            v-bind="attrs"
            text
            :disabled="disabled"
            outlined
            class="ms-2"
            v-on="on"
            @click="ignore(false)"
          >
            {{ $t('ignore_buttons.unignore') }}
          </v-btn>
        </template>
        <span>{{ $t('ignore_buttons.unignore_tooltip') }}</span>
      </v-tooltip>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class IgnoreButtons extends Vue {
  @Prop({ required: false, type: Boolean, default: false })
  disabled!: boolean;

  @Emit()
  ignore(_value: boolean) {}
}
</script>

<style scoped lang="scss"></style>
