export interface ParsedDeviceLimitError {
  hasLink: boolean;
  parts: string[];
}

/**
 * The backend marks the spot where a "learn more about premium devices" link should go
 * with this placeholder, so the frontend can render a real anchor mid-sentence.
 */
const DEVICE_LIMIT_PLACEHOLDER = '_DEVICE_LIMIT_LINK_';

/**
 * Splits a create-account error message around the device-limit link placeholder.
 *
 * @param error the raw error message from the backend
 * @returns whether a link should be rendered, and the message parts to render around it
 */
export function parseDeviceLimitError(error: string): ParsedDeviceLimitError {
  if (!error || !error.includes(DEVICE_LIMIT_PLACEHOLDER)) {
    return {
      hasLink: false,
      parts: [error],
    };
  }

  return {
    hasLink: true,
    parts: error.split(DEVICE_LIMIT_PLACEHOLDER),
  };
}
