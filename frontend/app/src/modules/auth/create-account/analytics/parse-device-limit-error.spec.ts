import { describe, expect, it } from 'vitest';
import { parseDeviceLimitError } from './parse-device-limit-error';

describe('modules/auth/create-account/analytics/parseDeviceLimitError', () => {
  it('should report no link for a plain message', () => {
    expect(parseDeviceLimitError('Something went wrong')).toEqual({
      hasLink: false,
      parts: ['Something went wrong'],
    });
  });

  it('should split the message around the placeholder', () => {
    expect(parseDeviceLimitError('You reached the limit._DEVICE_LIMIT_LINK_Please retry.')).toEqual({
      hasLink: true,
      parts: ['You reached the limit.', 'Please retry.'],
    });
  });

  it('should keep an empty leading part when the placeholder starts the message', () => {
    expect(parseDeviceLimitError('_DEVICE_LIMIT_LINK_trailing')).toEqual({
      hasLink: true,
      parts: ['', 'trailing'],
    });
  });

  it('should keep an empty trailing part when the placeholder ends the message', () => {
    expect(parseDeviceLimitError('leading_DEVICE_LIMIT_LINK_')).toEqual({
      hasLink: true,
      parts: ['leading', ''],
    });
  });

  it('should not match a near-miss placeholder', () => {
    expect(parseDeviceLimitError('DEVICE_LIMIT_LINK without underscores')).toEqual({
      hasLink: false,
      parts: ['DEVICE_LIMIT_LINK without underscores'],
    });
  });

  it('should treat an empty message as linkless', () => {
    expect(parseDeviceLimitError('')).toEqual({
      hasLink: false,
      parts: [''],
    });
  });
});
