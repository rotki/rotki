import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AboutDataDirectory from '@/modules/shell/components/AboutDataDirectory.vue';
import CopyButton from '@/modules/shell/components/CopyButton.vue';

interface Props {
  dataDirectory?: string;
  isPackaged?: boolean;
}

function mountDataDirectory(props: Props = {}): VueWrapper<InstanceType<typeof AboutDataDirectory>> {
  return mount(AboutDataDirectory, {
    props: { dataDirectory: '/home/user/.rotki', ...props },
  });
}

describe('modules/shell/components/AboutDataDirectory', () => {
  it('should render the data directory path', () => {
    const wrapper = mountDataDirectory();
    expect(wrapper.text()).toContain('/home/user/.rotki');
  });

  it('should show the copy button when not packaged', () => {
    const wrapper = mountDataDirectory({ isPackaged: false });
    expect(wrapper.findComponent(CopyButton).exists()).toBe(true);
  });

  it('should show the open-folder action when packaged and emit open-path', async () => {
    const wrapper = mountDataDirectory({ isPackaged: true });
    expect(wrapper.findComponent(CopyButton).exists()).toBe(false);
    await wrapper.find('button').trigger('click');
    expect(wrapper.emitted('open-path')).toHaveLength(1);
  });
});
