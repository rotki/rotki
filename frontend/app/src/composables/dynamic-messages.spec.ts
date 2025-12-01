import type { Pinia } from 'pinia';
import type { DashboardMessage, WelcomeMessage } from '@/types/dynamic-messages';
import { server } from '@test/setup-files/server';
import dayjs from 'dayjs';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { serializer, useDynamicMessages } from '@/composables/dynamic-messages';
import { camelCaseTransformer } from '@/modules/api/transformers';
import { usePremiumStore } from '@/store/session/premium';

const period = {
  start: dayjs('2023/10/11').unix(),
  end: dayjs('2023/10/13').unix(),
};

const action = {
  text: 'action',
  url: 'https://url',
};

const testDash: DashboardMessage = {
  message: 'msg',
  messageHighlight: 'high',
  action,
  period,
};

const testWelcome: WelcomeMessage = {
  header: 'h',
  icon: 'https://icon.svg',
  text: 'text',
  action,
  period,
};

describe('useDynamicMessages', () => {
  let pinia: Pinia;
  let store: ReturnType<typeof usePremiumStore>;

  beforeEach(() => {
    if (!pinia) {
      pinia = createPinia();
      setActivePinia(pinia);
      store = usePremiumStore();
    }

    // Clear session storage
    sessionStorage.clear();

    // Reset premium to false for each test
    const { premium } = storeToRefs(store);
    set(premium, false);
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('show valid period dashboard message', async () => {
    const { activeDashboardMessages, fetchMessages } = useDynamicMessages();

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([testDash], { status: 200 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({}, { status: 404 })),
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    expect(get(activeDashboardMessages)[0]).toMatchObject(camelCaseTransformer(testDash));
  });

  it('do not show invalid period dashboard message', async () => {
    const { activeDashboardMessages, fetchMessages } = useDynamicMessages();

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([testDash], { status: 200 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({}, { status: 404 })),
    );
    vi.setSystemTime(dayjs('2023/10/15').toDate());
    await fetchMessages();

    expect(get(activeDashboardMessages)[0]).toBeUndefined();
  });

  it('show valid period welcome message', async () => {
    const { welcomeMessage, fetchMessages } = useDynamicMessages();

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([], { status: 404 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({ messages: [testWelcome] }, { status: 200 })),
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    expect(get(welcomeMessage)).toMatchObject(camelCaseTransformer(testWelcome));
  });

  it('should not show invalid period welcome message', async () => {
    const { welcomeMessage, fetchMessages } = useDynamicMessages();

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([], { status: 404 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({ messages: [testWelcome] }, { status: 200 })),
    );
    vi.setSystemTime(dayjs('2023/10/10').toDate());
    await fetchMessages();

    expect(get(welcomeMessage)).toBeNull();
  });

  it('should show custom header if data is set', async () => {
    const { welcomeHeader, fetchMessages } = useDynamicMessages();

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([], { status: 404 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({ header: 'test', text: 'test', messages: [] }, { status: 200 })),
    );

    await fetchMessages();
    expect(get(welcomeHeader)).toStrictEqual({
      header: 'test',
      text: 'test',
    });
  });

  it('should show default header if data is no set', async () => {
    const { welcomeHeader, fetchMessages } = useDynamicMessages();

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([], { status: 404 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({}, { status: 404 })),
    );

    await fetchMessages();
    expect(get(welcomeHeader)).toBeNull();
  });

  it('should show target free message to free users', async () => {
    const { activeDashboardMessages, fetchMessages } = useDynamicMessages();

    const freeUserMessage: DashboardMessage = {
      ...testDash,
      target: 'free',
    };

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([freeUserMessage], { status: 200 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({}, { status: 404 })),
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    expect(get(activeDashboardMessages)).toHaveLength(1);
    expect(get(activeDashboardMessages)[0]).toMatchObject(camelCaseTransformer(freeUserMessage));
  });

  it('should not show target free message to premium users', async () => {
    const store = usePremiumStore();
    const { premium } = storeToRefs(store);
    set(premium, true);

    const { activeDashboardMessages, fetchMessages } = useDynamicMessages();

    const freeUserMessage: DashboardMessage = {
      ...testDash,
      target: 'free',
    };

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([freeUserMessage], { status: 200 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({}, { status: 404 })),
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    // Verify premium status is correctly set
    expect(get(premium)).toBe(true);
    expect(get(activeDashboardMessages)).toHaveLength(0);
  });

  it('should show target premium message to premium users', async () => {
    const store = usePremiumStore();
    const { premium } = storeToRefs(store);
    set(premium, true);

    const { activeDashboardMessages, fetchMessages } = useDynamicMessages();

    const premiumUserMessage: DashboardMessage = {
      ...testDash,
      target: 'premium',
    };

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([premiumUserMessage], { status: 200 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({}, { status: 404 })),
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    expect(get(activeDashboardMessages)).toHaveLength(1);
    expect(get(activeDashboardMessages)[0]).toMatchObject(camelCaseTransformer(premiumUserMessage));
  });

  it('should not show target premium message to free users', async () => {
    const { activeDashboardMessages, fetchMessages } = useDynamicMessages();

    const premiumUserMessage: DashboardMessage = {
      ...testDash,
      target: 'premium',
    };

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([premiumUserMessage], { status: 200 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({}, { status: 404 })),
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    expect(get(activeDashboardMessages)).toHaveLength(0);
  });

  it('should show message without target to all users', async () => {
    const { activeDashboardMessages, fetchMessages } = useDynamicMessages();

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([testDash], { status: 200 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({}, { status: 404 })),
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    expect(get(activeDashboardMessages)).toHaveLength(1);
    expect(get(activeDashboardMessages)[0]).toMatchObject(camelCaseTransformer(testDash));
  });

  it('should filter multiple messages based on target', async () => {
    const store = usePremiumStore();
    const { premium } = storeToRefs(store);
    set(premium, true);

    const { activeDashboardMessages, fetchMessages } = useDynamicMessages();

    const freeUserMessage: DashboardMessage = {
      ...testDash,
      message: 'free user message',
      target: 'free',
    };

    const premiumUserMessage: DashboardMessage = {
      ...testDash,
      message: 'premium user message',
      target: 'premium',
    };

    const generalMessage: DashboardMessage = {
      ...testDash,
      message: 'general message',
    };

    server.use(
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json', () =>
        HttpResponse.json([freeUserMessage, premiumUserMessage, generalMessage], { status: 200 })),
      http.get('https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json', () =>
        HttpResponse.json({}, { status: 404 })),
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    const messages = get(activeDashboardMessages);
    expect(messages).toHaveLength(2);
    expect(messages[0]).toMatchObject(camelCaseTransformer(premiumUserMessage));
    expect(messages[1]).toMatchObject(camelCaseTransformer(generalMessage));
  });
});

describe('serializer', () => {
  it('serializes and deserializes correctly', () => {
    const data = { key: 'value', number: 42 };

    const serialized = serializer.write(data);
    expect(serialized).toBe('{"key":"value","number":42}');

    const deserialized = serializer.read(serialized);
    expect(deserialized).toEqual(data);
  });

  it('handles null/empty values', () => {
    expect(serializer.read(null)).toBeNull();
    expect(serializer.read('')).toBeNull();
    expect(serializer.read(undefined)).toBeNull();
  });
});
