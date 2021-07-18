<template>
  <v-chip
    class="tag font-weight-medium"
    label
    :small="small"
    :color="`#${tag.background_color}`"
    :text-color="`#${tag.foreground_color}`"
  >
    {{ tag.name }}
  </v-chip>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { Tag } from '@/typing/types';

@Component({})
export default class TagIcon extends Vue {
  @Prop({ required: true })
  tag!: Tag;
  @Prop({ required: false, type: Boolean, default: false })
  small!: boolean;
}
</script>

<style scoped lang="scss"></style>
