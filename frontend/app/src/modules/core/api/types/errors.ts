import { isEmpty } from 'es-toolkit/compat';
import { camelCaseTransformer } from '@/modules/core/api/transformers';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';

/**
 * Converts a stringified JSON returned from the API to JSON.
 *
 * @remarks
 * Use {@link ApiValidationError} in the catch clause instead.
 *
 * @param message - a stringified JSON message
 * @returns the parsed object, or `undefined` when the message is not JSON
 */
function deserializeApiErrorMessage(message: string): Record<string, string[]> | undefined {
  try {
    return JSON.parse(message);
  }
  catch {
    return undefined;
  }
}

export type ValidationErrors = Record<string, string[] | string>;

/**
 * The JSON-RPC shape of a thrown value: a message plus the optional `code`/`data` an RPC provider
 * attaches. Wallet errors arrive as `unknown` and are only ever read for these three fields.
 */
export interface RpcError {
  readonly message: string;
  readonly code?: number;
  readonly data?: unknown;
}

/**
 * Reads the RPC fields off an unknown thrown value, keeping only what is actually there and of the
 * right type. Unlike asserting the error into a coded shape, a caller reading `code` here is reading
 * a value that was checked.
 */
export function toRpcError(error: unknown): RpcError {
  const message = getErrorMessage(error);

  if (typeof error !== 'object' || error === null)
    return { message };

  return {
    code: 'code' in error && typeof error.code === 'number' ? error.code : undefined,
    data: 'data' in error ? error.data : undefined,
    message,
  };
}

export class ApiKeyMissingError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = 'ApiKeyMissingError';
  }
}

export class ApiValidationError extends Error {
  readonly errors: ValidationErrors;
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = 'ApiValidationError';
    this.errors = camelCaseTransformer(deserializeApiErrorMessage(message)) ?? {};
  }

  getValidationErrors(payload: Record<string, any>): ValidationErrors | string {
    const errors = this.errors;
    const errorKeys = Object.keys(errors);
    const payloadKeys = Object.keys(payload);

    if (Object.keys(payload).length > 0) {
      for (const errorKey of errorKeys) {
        if (!payloadKeys.includes(errorKey)) {
          const entry = errors[errorKey];
          if (typeof entry === 'string')
            return entry;

          return entry[0] || '';
        }
      }
    }

    if (!isEmpty(errors))
      return errors;

    return this.message;
  }
}
