import dayjs from 'dayjs';

describe('utils/date', () => {
  setupDayjs();
  test('check return value of guessTimezone function', () => {
    expect(guessTimezone()).toBeTruthy();
    expect(guessTimezone()).toBeTypeOf('string');
  });

  test('check converted date matches with timezone applied', () => {
    const utcDate = dayjs
      .utc('2013-11-18 11:55:20')
      .tz(guessTimezone())
      .toString();
    const utcTzDate = dayjs.utc('2013-11-18 11:55:20').toString();
    expect(utcDate).toEqual(utcTzDate);
  });
});
