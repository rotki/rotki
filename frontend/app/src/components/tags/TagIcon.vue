<template>
  <v-chip
    class="tag font-weight-medium"
    label
    :small="small"
    :color="`#${tag.backgroundColor}`"
    :text-color="`#${tag.foregroundColor}`"
  >
    {{ tag.name }}
  </v-chip>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { Tag } from '@/types/user';

@Component({})
export default class TagIcon extends Vue {
  @Prop({ required: true })
  tag!: Tag;
  @Prop({ required: false, type: Boolean, default: false })
  small!: boolean;
}
</script>
