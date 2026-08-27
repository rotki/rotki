import { assert } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import DockerWarning from './DockerWarning.vue';
import '@test/i18n';

describe('dockerWarning', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  const createWrapper = (): VueWrapper => mount(DockerWarning);

  it('should offer the command that configures a session key', () => {
    expect(createWrapper().text()).toContain('ROTKI_SESSION_KEY=$(openssl rand -hex 32)');
  });

  it('should link to the session authentication documentation', () => {
    const link = createWrapper().findComponent(ExternalLink);
    expect(link.props('url')).toContain('#session-authentication');
  });

  it('should name the variable that accepts an unauthenticated api permanently', () => {
    expect(createWrapper().text()).toContain('ROTKI_ACCEPT_UNAUTHENTICATED_API');
  });

  it('should accept the risk when the user proceeds', async () => {
    const { unauthenticatedApiAccepted } = storeToRefs(useMainStore());
    set(unauthenticatedApiAccepted, false);

    const wrapper = createWrapper();
    const accept = wrapper.findAll('button').find(button => button.text().includes('docker_warning.accept'));
    assert(accept, 'the accept button should be rendered');
    await accept.trigger('click');

    expect(get(unauthenticatedApiAccepted)).toBe(true);
  });
});
