import { Component, Vue } from 'vue-property-decorator';
import { Section, Status } from '@/store/const';
import { getStatus } from '@/store/utils';
import { assert } from '@/utils/assertions';

@Component({})
export default class StatusMixin extends Vue {
  // The default value of the mixing. Implementers are required to set that.
  section: Section = Section.NONE;
  secondSection: Section = Section.NONE;

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
    const status = getStatus(section);
    return !(
      status === Status.LOADED ||
      status === Status.PARTIALLY_LOADED ||
      status === Status.REFRESHING
    );
  }

  isRefreshing(section: Section): boolean {
    assert(section !== Section.NONE);
    const status = getStatus(section);
    return (
      status === Status.LOADING ||
      status === Status.REFRESHING ||
      status === Status.PARTIALLY_LOADED
    );
  }
}
