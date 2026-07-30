import type { APIRequestContext } from '@playwright/test';
import { backendUrl } from '../../../playwright.config';

/**
 * Payload for adding an EVM event. Timestamps are milliseconds and addresses must be
 * checksummed — the backend rejects anything else.
 */
export interface EvmEventSeed {
  txRef: string;
  location: string;
  timestamp: number;
  sequenceIndex: number;
  eventType: string;
  eventSubtype: string;
  asset: string;
  amount: string;
  counterparty?: string;
  address?: string;
  locationLabel?: string;
  notes?: string;
}

/**
 * Adds an EVM history event via `PUT /api/1/history/events`.
 *
 * Seeding through the API rather than the add-event dialog keeps the filter specs about
 * filtering: a handful of events with deliberately distinct assets, protocols and addresses
 * would otherwise cost as many slow form round-trips before the first assertion.
 *
 * The referenced transaction must already exist in the user DB — see `seedEvmTransaction`.
 */
export async function apiAddEvmEvent(
  request: APIRequestContext,
  event: EvmEventSeed,
): Promise<number> {
  const response = await request.put(`${backendUrl}/api/1/history/events`, {
    failOnStatusCode: false,
    data: {
      address: event.address ?? null,
      amount: event.amount,
      asset: event.asset,
      counterparty: event.counterparty ?? null,
      entry_type: 'evm event',
      event_subtype: event.eventSubtype,
      event_type: event.eventType,
      location: event.location,
      location_label: event.locationLabel ?? null,
      sequence_index: event.sequenceIndex,
      timestamp: event.timestamp,
      tx_ref: event.txRef,
      user_notes: event.notes ?? null,
    },
  });

  const body = await response.json();

  if (!response.ok())
    throw new Error(`failed to add evm event ${event.txRef}: ${JSON.stringify(body)}`);

  return body.result.identifier;
}

/** Payload for adding a plain (non-EVM) history event, e.g. an exchange event. */
export interface OnlineEventSeed {
  groupIdentifier: string;
  location: string;
  timestamp: number;
  sequenceIndex: number;
  eventType: string;
  eventSubtype: string;
  asset: string;
  amount: string;
  locationLabel?: string;
  notes?: string;
}

/**
 * Adds a plain history event. Unlike an EVM event it needs no transaction to exist, and it
 * carries no counterparty — which is what makes it useful for asserting that an entry-type
 * exclusion filter really excludes.
 */
export async function apiAddOnlineEvent(
  request: APIRequestContext,
  event: OnlineEventSeed,
): Promise<number> {
  const response = await request.put(`${backendUrl}/api/1/history/events`, {
    failOnStatusCode: false,
    data: {
      amount: event.amount,
      asset: event.asset,
      entry_type: 'history event',
      event_subtype: event.eventSubtype,
      event_type: event.eventType,
      group_identifier: event.groupIdentifier,
      location: event.location,
      location_label: event.locationLabel ?? null,
      sequence_index: event.sequenceIndex,
      timestamp: event.timestamp,
      user_notes: event.notes ?? null,
    },
  });

  const body = await response.json();

  if (!response.ok())
    throw new Error(`failed to add online event ${event.groupIdentifier}: ${JSON.stringify(body)}`);

  return body.result.identifier;
}
