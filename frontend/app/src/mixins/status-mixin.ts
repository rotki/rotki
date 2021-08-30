import { Component, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import { Section, Status } from '@/store/const';
import { assert } from '@/utils/assertions';

@Component({
  computed: {
    ...mapGetters(['status'])
  }
})
export default class StatusMixin extends Vue {
  // The default value of the mixing. Implementers are required to set that.
  section: Section = Section.NONE;
  secondSection: Section = Section.NONE;
  status!: (section: Section) => Status;

  get loading(): boolean {
    return this.isLoading(this.section);
  }

  get refreshing(): boolean {
    return this.isRefreshing(this.section);
  }

  get secondaryLoading(): boolean {
    return this.isLoading(this.secondSection);
  }

  get secondaryRefreshing(): boolean {
    return this.isRefreshing(this.secondSection);
  }

  get anyLoading(): boolean {
    return this.loading || this.secondaryLoading;
  }

  get anyRefreshing(): boolean {
    return this.refreshing || this.secondaryRefreshing;
  }

  isLoading(section: Section): boolean {
    assert(section !== Section.NONE);
    const status = this.status(section);
    return !(
      status === Status.LOADED ||
      status === Status.PARTIALLY_LOADED ||
      status === Status.REFRESHING
    );
  }

  isRefreshing(section: Section): boolean {
    assert(section !== Section.NONE);
    const status = this.status(section);
    return (
      status === Status.LOADING ||
      status === Status.REFRESHING ||
      status === Status.PARTIALLY_LOADED
    );
  }
}
