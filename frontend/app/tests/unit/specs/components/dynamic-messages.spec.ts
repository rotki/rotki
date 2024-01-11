import { HttpResponse, http } from 'msw';
import { expect } from 'vitest';
import dayjs from 'dayjs';
import {
  type DashboardMessage,
  type WelcomeMessage
} from '@/types/dynamic-messages';
import { camelCaseTransformer } from '@/services/axios-tranformers';
import { server } from '../../setup-files/server';

const period = {
  start: dayjs('2023/10/11').unix(),
  end: dayjs('2023/10/13').unix()
};

const action = {
  text: 'action',
  url: 'https://url'
};

const testDash: DashboardMessage = {
  message: 'msg',
  message_highlight: 'high',
  action,
  period
};

const testWelcome: WelcomeMessage = {
  header: 'h',
  icon: 'https://icon.svg',
  text: 'text',
  action,
  period
};

describe('useDynamicMessages', () => {
  test('show valid period dashboard message', async () => {
    const { dashboardMessage, fetchMessages } = useDynamicMessages();

    server.use(
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json',
        () => HttpResponse.json([testDash], { status: 200 })
      ),
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json',
        () => HttpResponse.json({}, { status: 404 })
      )
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    expect(get(dashboardMessage)).toMatchObject(camelCaseTransformer(testDash));
  });

  test('do not show invalid period dashboard message', async () => {
    const { dashboardMessage, fetchMessages } = useDynamicMessages();

    server.use(
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json',
        () => HttpResponse.json([testDash], { status: 200 })
      ),
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json',
        () => HttpResponse.json({}, { status: 404 })
      )
    );
    vi.setSystemTime(dayjs('2023/10/15').toDate());
    await fetchMessages();

    expect(get(dashboardMessage)).toBeNull();
  });

  test('show valid period welcome message', async () => {
    const { welcomeMessage, fetchMessages } = useDynamicMessages();

    server.use(
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json',
        () => HttpResponse.json([], { status: 404 })
      ),
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json',
        () => HttpResponse.json({ messages: [testWelcome] }, { status: 200 })
      )
    );
    vi.setSystemTime(dayjs('2023/10/12').toDate());
    await fetchMessages();

    expect(get(welcomeMessage)).toMatchObject(
      camelCaseTransformer(testWelcome)
    );
  });

  test('should not show invalid period welcome message', async () => {
    const { welcomeMessage, fetchMessages } = useDynamicMessages();

    server.use(
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json',
        () => HttpResponse.json([], { status: 404 })
      ),
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json',
        () => HttpResponse.json({ messages: [testWelcome] }, { status: 200 })
      )
    );
    vi.setSystemTime(dayjs('2023/10/10').toDate());
    await fetchMessages();

    expect(get(welcomeMessage)).toBeNull();
  });

  test('should show custom header if data is set', async () => {
    const { welcomeHeader, fetchMessages } = useDynamicMessages();

    server.use(
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json',
        () => HttpResponse.json([], { status: 404 })
      ),
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json',
        () =>
          HttpResponse.json(
            { header: 'test', text: 'test', messages: [] },
            { status: 200 }
          )
      )
    );

    await fetchMessages();
    expect(get(welcomeHeader)).toStrictEqual({
      header: 'test',
      text: 'test'
    });
  });

  test('should show default header if data is no set', async () => {
    const { welcomeHeader, fetchMessages } = useDynamicMessages();

    server.use(
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/dashboard.json',
        () => HttpResponse.json([], { status: 404 })
      ),
      http.get(
        'https://raw.githubusercontent.com/rotki/data/develop/messages/welcome.json',
        () => HttpResponse.json({}, { status: 404 })
      )
    );

    await fetchMessages();
    expect(get(welcomeHeader)).toBeNull();
  });
});
