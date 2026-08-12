import { type APIRequestContext, type Browser, expect } from '@playwright/test';
import { TEST_EVENT_TIMESTAMP, TEST_PRICE_ENTRIES } from '../../fixtures/history-events';
import {
  A_USDC,
  A_USDC_OPTIMISM,
  ADDRESS_ALPHA,
  ADDRESS_BETA,
  DATE_CUTOFF_DIGITS,
  DATE_CUTOFF_TYPED,
  EVENTS_AFTER_CUTOFF,
  multiChainChainIds,
  multiChainEvents,
  NOTE_PREFIX,
  PAGE_SIZE,
  PAGED_KRAKEN,
  PAGED_TOTAL,
  pagedEvents,
  pillFilterChainIds,
  pillFilterEvents,
  pillFilterOnlineEvent,
  TOTAL_SEEDED_EVENTS,
} from '../../fixtures/pill-filter';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { apiAddEvmEvent, apiAddOnlineEvent } from '../../helpers/history-events-api';
import { seedBlockchainAccounts, seedEvmTransaction, seedHistoricPrices } from '../../helpers/seed-db';
import { HistoryEventsPage } from '../../pages/history-events-page';
import { PillFilterBar } from '../../pages/pill-filter-bar';
import { PillViewsMenu } from '../../pages/pill-views-menu';
import { RotkiApp } from '../../pages/rotki-app';

const ROW = '[data-testid=history-event-row]';

/**
 * Regression net for the pill filter bar on the history events table.
 *
 * The events are seeded through the API (see `fixtures/pill-filter`) with deliberately distinct
 * assets, protocols, addresses and amounts, so every filter dimension narrows to a different
 * row count. Each assertion pairs the visible row count with the URL, since the URL is the
 * shareable form of the filter and the two drifting apart is the failure worth catching.
 *
 * Nothing here waits for the task queue to drain. The seeded tracked accounts keep a balance
 * query running that filtering does not depend on, so the gate is the row count settling on its
 * expected value — which is the thing under test anyway.
 */
/**
 * Creates a user, seeds the event set into it, and logs in.
 *
 * The order matters: the backend does not reliably see rows written into a user DB it already
 * holds open, so the database is created, released by logging out, seeded while nothing holds
 * it, and only then reopened by logging in.
 *
 * Logging in goes through the form rather than `fasterLogin`, which authenticates over the API
 * first: with the backend already holding that session the form submit does not take and the
 * suite sits on "Unlock account". `checkGetPremiumButton` pins the app as actually loaded, since
 * `login()` assumes success when neither post-login dialog appears in time.
 */
async function seedPillFilterUser(
  browser: Browser,
  request: APIRequestContext,
): Promise<SharedTestContext> {
  const ctx = await createLoggedInContext(browser, request, {
    // The mock answers an unrecorded call immediately, where real nodes would keep the balance
    // query the seeded addresses trigger alive past the test timeout.
    rpcMockCassette: 'pill-filter',
    seed: (username) => {
      seedHistoricPrices(TEST_PRICE_ENTRIES, TEST_EVENT_TIMESTAMP);

      for (const [txHash, chainId] of Object.entries(pillFilterChainIds))
        seedEvmTransaction(username, txHash, chainId);

      // The account pill offers the tracked addresses, so they have to exist before login.
      seedBlockchainAccounts(username, [ADDRESS_ALPHA, ADDRESS_BETA]);
    },
  });

  for (const event of pillFilterEvents)
    await apiAddEvmEvent(request, event);

  await apiAddOnlineEvent(request, pillFilterOnlineEvent);

  return ctx;
}

test.describe.serial('history events pill filter', () => {
  let ctx: SharedTestContext;
  let page: HistoryEventsPage;
  let bar: PillFilterBar;
  let views: PillViewsMenu;

  async function expectRows(count: number): Promise<void> {
    await expect.poll(async () => ctx.sharedPage.locator(ROW).count(), { timeout: 15000 }).toBe(count);
  }

  function url(): string {
    return ctx.sharedPage.url();
  }

  test.beforeAll(async ({ browser, request }) => {
    ctx = await seedPillFilterUser(browser, request);
    page = new HistoryEventsPage(ctx.sharedPage);
    bar = new PillFilterBar(ctx.sharedPage);
    views = new PillViewsMenu(ctx.sharedPage);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('seeded events all render with an empty bar', async () => {
    await page.visit();
    await bar.waitForVisible();

    await expectRows(TOTAL_SEEDED_EVENTS);
    expect(await bar.pillCount()).toBe(0);
  });

  test('adding a protocol filter from the add menu narrows the table', async () => {
    await bar.addField('counterparties');
    await bar.selectValue('uniswap-v2', 'uniswap');
    await bar.closeEditor();

    await bar.expectPillVisible('counterparties');
    // The pill shows the protocol's display name, not its wire id.
    expect(await bar.pillValue('counterparties')).toContain('Uniswap');

    await expectRows(2);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('counterparties=uniswap-v2');
  });

  test('removing the pill restores every row', async () => {
    await bar.removePill('counterparties');

    await bar.expectNoPill('counterparties');
    await expectRows(TOTAL_SEEDED_EVENTS);
    await expect.poll(() => url(), { timeout: 10000 }).not.toContain('counterparties=');
  });

  test('typing a field name in the bar offers that field and opens its editor', async () => {
    await bar.narrow('Protoc');
    await bar.expectFieldSuggestion('counterparties');
    await bar.pickFieldSuggestion('counterparties');

    // Picking a field adds an empty pill and opens its value editor straight away.
    await bar.expectPillVisible('counterparties');
    await bar.selectValue('curve');
    await bar.closeEditor();

    await expectRows(2);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('counterparties=curve');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // Narrowing matches a value's *display label*, never its wire id, so the query here is the
  // label ("Optimism"), not the value (`optimism`). Only one location carries that label, which
  // keeps the row it offers stable regardless of how long the location list grows.
  test('typing a value in the bar applies the filter in one step', async () => {
    await bar.narrow('Optimism');
    await bar.expectValueSuggestion('location', 'optimism');
    await bar.pickValueSuggestion('location', 'optimism');

    await bar.expectPillVisible('location');
    await expectRows(1);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('location=optimism');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('a free-text field rejects an invalid value and commits a valid one', async () => {
    await bar.addField('addresses');

    // Not an address: the editor must not offer it as valid, and nothing reaches the URL.
    await bar.typeTextValue('not-an-address');
    expect(await bar.textValueIsValid()).toBe(false);
    expect(url()).not.toContain('addresses=');

    await bar.typeTextValue(ADDRESS_ALPHA);
    await bar.closeEditor();

    await expectRows(2);
    await expect.poll(() => url(), { timeout: 10000 }).toContain(`addresses=${ADDRESS_ALPHA}`);

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('a notes filter matches on a substring', async () => {
    await bar.addField('notesSubstring');
    await bar.typeTextValue(`${NOTE_PREFIX} gamma`);
    await bar.closeEditor();

    await expectRows(1);
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('an amount range narrows, and switching the operator drops the hidden bound', async () => {
    await bar.addField('amount');
    await bar.setRangeBound('min', '100');
    await bar.setRangeBound('max', '1000');
    await bar.commitRange();

    await expectRows(1);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('minAmount=100');
    expect(url()).toContain('maxAmount=1000');

    // Switching to "greater than" leaves no upper bound, so it must leave the URL too —
    // a stale maxAmount would silently keep filtering.
    await bar.pill('amount').click();
    await bar.selectOperator('gt');
    await bar.closeEditor();

    await expect.poll(() => url(), { timeout: 10000 }).not.toContain('maxAmount=');
    expect(url()).toContain('minAmount=100');
    await expectRows(2);

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // Closing an editor commits rather than cancels. The range and notes editors push their value
  // through a debounce, so dismissing inside that window used to discard what was typed.
  test('a range dismissed without enter is still committed', async () => {
    await bar.addField('amount');
    await bar.setRangeBound('min', '100');
    // No enter: leave straight away, while the commit is still pending.
    await bar.dismissEditor();

    await expectRows(2);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('minAmount=100');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // Regression: clearing a pill left the bar still believing that field's editor was open, so
  // adding the same field again changed nothing and no editor appeared. Only visible in a real
  // browser — the unit spec stubs the menu to render its content inline either way.
  test('re-adding a cleared field opens its editor again', async () => {
    await bar.addField('counterparties');
    await bar.selectValue('curve');
    await bar.closeEditor('counterparties');
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);

    await bar.addField('counterparties');
    // The editor has to come back up, not just the pill.
    await expect(ctx.sharedPage.locator('[data-testid=value-select-search]')).toBeVisible();
    await bar.selectValue('curve');
    await bar.closeEditor('counterparties');

    await expectRows(2);
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('backspace on the empty input drops the last pill', async () => {
    await bar.narrow('Optimism');
    await bar.pickValueSuggestion('location', 'optimism');
    await bar.expectPillVisible('location');

    await bar.clearNarrowInput();
    await bar.pressInNarrow('Backspace');

    await bar.expectNoPill('location');
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('filters survive navigating away and back', async () => {
    await bar.narrow('Optimism');
    await bar.pickValueSuggestion('location', 'optimism');
    await bar.expectPillVisible('location');
    await expectRows(1);

    await RotkiApp.navigateTo(ctx.sharedPage, 'dashboard');
    await expect.poll(() => url(), { timeout: 10000 }).toContain('/dashboard');

    await page.visit();
    await bar.waitForVisible();

    await bar.expectPillVisible('location');
    await expect.poll(() => url(), { timeout: 10000 }).toContain('location=optimism');
    await expectRows(1);

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('several values in one field widen, and a second pill narrows again', async () => {
    await bar.addField('counterparties');
    await bar.selectValue('uniswap-v2', 'uniswap');
    // A multi-select field keeps its editor open, so the second value needs no reopening.
    await bar.selectValue('curve');
    await bar.closeEditor();

    await expectRows(4);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('uniswap-v2');
    expect(url()).toContain('curve');

    // A second pill is an AND: of the four protocol rows, only `gamma` is a spend.
    await bar.addField('eventTypes');
    await bar.selectValue('spend');
    await bar.closeEditor();

    await bar.expectPillVisible('counterparties');
    await bar.expectPillVisible('eventTypes');
    await expectRows(1);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('eventTypes=spend');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // Entry type is the one field allowing exclusion, and the operator model is what closes #11019.
  test('an is-not filter excludes rather than includes', async () => {
    await bar.addField('entryTypes');
    await bar.selectOperator('is_not');
    await bar.selectValue('evm event', 'evm');
    await bar.closeEditor();

    // Everything except the five EVM events, i.e. the one plain history event.
    await expectRows(TOTAL_SEEDED_EVENTS - pillFilterEvents.length);
    // A non-default operator is spelled out on the pill; the default `is` stays hidden.
    expect(await bar.pillText('entryTypes')).toContain('is not');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // The other direction of the codec: nav-and-back replays in-memory state, while a cold load
  // has to rebuild the pills from the query string alone. That is the shareable-link promise.
  test('loading a url that already carries filters rebuilds the pills', async () => {
    await ctx.sharedPage.goto('/#/history/events?counterparties=curve');
    await bar.waitForVisible();

    await bar.expectPillVisible('counterparties');
    expect(await bar.pillValue('counterparties')).toContain('Curve');
    await expectRows(2);

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // The asset field is the only one whose values are fetched rather than listed, so its editor
  // drives a remote search instead of filtering a local list.
  test('the asset editor filters on a remotely searched asset', async () => {
    await bar.addField('asset');
    await bar.selectValue(A_USDC, 'USDC');
    await bar.closeEditor('asset');

    await expectRows(1);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('asset=');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // Asset suggestions reach the bar's inline list asynchronously and are appended after the
  // synchronous ones, which is where a stale response or a moving highlight would show up.
  //
  // Which asset ranks first is the remote search's business, not the bar's: `USDC` exists on
  // many chains and only the first few survive the per-field cap. So this asserts that an async
  // row arrives and applies in one step, and leaves picking an exact asset to the editor test.
  test('the bar offers a remotely searched asset as a value suggestion', async () => {
    await bar.narrow('USDC');
    await bar.pickFirstValueSuggestion('asset');

    await bar.expectPillVisible('asset');
    await expect.poll(() => url(), { timeout: 10000 }).toContain('asset=');
    // Whichever USDC it picked, it must actually filter: at most the one seeded USDC event.
    await expect.poll(async () => ctx.sharedPage.locator(ROW).count(), { timeout: 15000 })
      .toBeLessThanOrEqual(1);

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('a free-text field refuses to add the same value twice', async () => {
    await bar.addField('addresses');
    await bar.typeTextValue(ADDRESS_ALPHA);
    await expectRows(2);

    // The second attempt is refused out loud rather than silently swallowed.
    await bar.typeTextValue(ADDRESS_ALPHA);
    expect((await bar.textFieldError()).toLowerCase()).toContain('already added');
    await bar.closeEditor();

    await expectRows(2);
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // A free-text field has no option list, so a value it was filtered by before is the only thing
  // the bar can offer for it. The bucket is persisted as a frontend setting.
  test('a value used before is offered again by the bar', async () => {
    const note = `${NOTE_PREFIX} gamma`;

    await bar.addField('notesSubstring');
    await bar.typeTextValue(note);
    await bar.closeEditor();
    await expectRows(1);
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);

    await bar.narrow(`${NOTE_PREFIX} gamm`);
    await bar.expectValueSuggestion('notesSubstring', note);
    await bar.pickValueSuggestion('notesSubstring', note);

    await expectRows(1);
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('a date bound filters to the events after it', async () => {
    await bar.addField('period');
    await bar.selectOperator('after');
    await bar.setDateBound('from', DATE_CUTOFF_DIGITS);
    await bar.closeEditor();

    await expectRows(EVENTS_AFTER_CUTOFF);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('fromTimestamp=');
    // "after" carries no upper bound, so none may reach the wire.
    expect(url()).not.toContain('toTimestamp=');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // The account pill is the bar's only param-bound field: it does not travel through `matches`
  // like every other filter, but through a separate param source that feeds the request and the
  // URL as `locationLabels`. That second binding is a distinct branch of the codec.
  test('the account pill filters through its param binding', async () => {
    await bar.addField('account');
    await bar.selectValue(ADDRESS_ALPHA, ADDRESS_ALPHA.toLowerCase());
    await bar.closeEditor('account');

    await bar.expectPillVisible('account');
    // Both `alpha` and `beta` events carry this address as their location label.
    await expectRows(2);
    await expect.poll(() => url(), { timeout: 10000 }).toContain(`locationLabels=${ADDRESS_ALPHA}`);

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // The state pill is the first field bound to a param that goes to BOTH the request and the URL,
  // and the only one whose read-back is hand-written rather than codec-generic: the route's
  // comma-joined `stateMarkers` is split and validated in `applyHistoryEventRouteQuery`, then
  // bridged into the bar's param bag. Loading a URL that carries it is the only way to drive that
  // direction — the account pill covers state -> URL, and the matcher fields cover URL -> pill,
  // but nothing covers URL -> pill for a param. The failure it guards is quiet: the filter still
  // reaches the request while its pill silently never appears.
  //
  // Deliberately no row assertion. No seeded event is customized (that state is derived by the
  // backend from an edit), so the rows here say nothing about the binding under test.
  test('a url carrying a state marker rebuilds its pill', async () => {
    await ctx.sharedPage.goto('/#/history/events?stateMarkers=customized');
    await bar.waitForVisible();

    await bar.expectPillVisible('state');
    expect(await bar.pillValue('state')).toContain('Customized');

    // And back out again: clearing the pill has to take the param with it, or the request keeps
    // filtering by a state the bar no longer shows.
    await bar.clearAll();
    await bar.expectNoPill('state');
    await expect.poll(() => url(), { timeout: 10000 }).not.toContain('stateMarkers');
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // A view stores both halves of the bar, so the pair under test is deliberately one matcher pill
  // (location) and one param pill (account): the account is exactly what the old saved-filter
  // shape could not express, and the failure worth catching is a view that comes back with only
  // half of what was saved.
  test('a saved view stores and restores both a matcher and a param pill', async () => {
    await views.open();
    // Nothing is filtered yet, so there is nothing to name.
    expect(await views.canSave()).toBe(false);
    await views.close();

    await bar.addField('location');
    await bar.selectValue('ethereum');
    await bar.closeEditor('location');
    await bar.addField('account');
    await bar.selectValue(ADDRESS_ALPHA, ADDRESS_ALPHA.toLowerCase());
    await bar.closeEditor('account');
    await expectRows(2);

    await views.open();
    await views.save('Alpha on mainnet');
    // The row says what it filters, so a view is recognisable by more than the name given to it.
    expect(await views.summary('Alpha on mainnet')).toContain('Ethereum');
    await views.close();

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);

    await views.open();
    await views.apply('Alpha on mainnet');

    await bar.expectPillVisible('location');
    await bar.expectPillVisible('account');
    await expectRows(2);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('location=ethereum');
    await expect.poll(() => url(), { timeout: 10000 }).toContain(`locationLabels=${ADDRESS_ALPHA}`);
  });

  // Deleting is the other half of the round trip, and it has to leave the applied filters alone:
  // removing a view is not the same gesture as clearing the bar.
  test('a saved view can be deleted without disturbing the filters it applied', async () => {
    await views.open();
    await views.remove('Alpha on mainnet');
    await views.expectEmpty();
    await views.close();

    await bar.expectPillVisible('location');
    await expectRows(2);

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // The whole menu, from opening it to applying a view, without touching the mouse. Only a real
  // browser can answer this: jsdom does not model focus or tab order, and every bug this menu has
  // had was a focus bug — the menu's own Escape handler is dead unless the list holds focus, and
  // saving used to strand focus on a button that had just disappeared.
  test('the views menu can be driven entirely from the keyboard', async () => {
    await bar.addField('location');
    await bar.selectValue('optimism');
    await bar.closeEditor('location');
    await expectRows(1);

    await views.open();
    // Opening lands focus on the list, which is where the arrow keys and Escape are handled.
    expect(await bar.focusedTestId()).toBe('pill-views-list');

    // The name field is one Tab away while the list holds no view of its own.
    await bar.pressFocused('Tab');
    expect(await bar.focusedTestId()).toBe('pill-views-name');
    await bar.typeFocused('kb optimism');
    await bar.pressFocused('Enter');

    // Saving hands focus back to the list, which now holds the view.
    await views.expectVisible('kb optimism');
    expect(await bar.focusedTestId()).toBe('pill-views-list');
    await views.close();

    // A second view, so moving the highlight is a move rather than a wrap onto itself. Saved with
    // the mouse: the keyboard save is proven above, and with a view in the list Tab lands on that
    // row rather than on the name field.
    // Location is single-select, so picking another value replaces the one already there.
    await bar.openPillEditor('location');
    await bar.selectValue('kraken');
    await bar.closeEditor('location');
    await expectRows(1);

    await views.open();
    // Tab out of the list reaches the stored view itself, so a row is reachable without a mouse.
    await bar.pressFocused('Tab');
    expect(await bar.focusedTestId()).toBe('pill-views-apply');
    // The index matters: Tab must land on the FIRST row, not merely on some row.
    expect(await bar.focusedIndex()).toBe('0');
    await views.save('kb kraken');
    await views.close();

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);

    // Down one row, then Enter: the second view, applied without a click.
    await views.open();
    await bar.pressFocused('ArrowDown');
    await bar.pressFocused('Enter');

    await bar.expectPillVisible('location');
    expect(await bar.pillValue('location')).toContain('Kraken');
    await expectRows(1);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('location=kraken');

    await views.open();
    await views.remove('kb optimism');
    await views.remove('kb kraken');
    await views.close();
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // An amount and a date are written, not picked, so before this the inline input had nothing to
  // offer for them: the query was only ever ranked against field labels and option values.
  test('a typed amount is offered as a filter in both directions', async () => {
    await bar.narrow('100');

    // Ambiguous on purpose: `100` cannot say which bound is meant, so both are offered.
    await bar.expectFilterSuggestion('amount', 'gt');
    await bar.expectFilterSuggestion('amount', 'lt');
    expect(await bar.filterSuggestionText('amount', 'gt')).toContain('greater than 100');

    await bar.pickFilterSuggestion('amount', 'gt');

    await bar.expectPillVisible('amount');
    await expectRows(2);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('minAmount=100');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('a written comparison is offered as the one bound it names', async () => {
    await bar.narrow('<50');

    await bar.expectFilterSuggestion('amount', 'lt');
    await bar.pickFilterSuggestion('amount', 'lt');

    // 1.5, 20, 0.25 and 7 are under 50; the 300 and 4000 events are not.
    await expectRows(4);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('maxAmount=50');
    expect(url()).not.toContain('minAmount=');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // The date field reads the query through the user's own date format, so this also pins that the
  // bar and the picker agree about what a written date means: same cutoff as the picker test above.
  test('a typed date is offered as a period filter', async () => {
    await bar.narrow(DATE_CUTOFF_TYPED);

    await bar.expectFilterSuggestion('period', 'after');
    await bar.expectFilterSuggestion('period', 'before');
    await bar.pickFilterSuggestion('period', 'after');

    await bar.expectPillVisible('period');
    await expectRows(EVENTS_AFTER_CUTOFF);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('fromTimestamp=1705320150');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // A number is an amount, not a year: the date field must not offer half-read rows for it.
  test('a bare number is not offered as a date', async () => {
    await bar.narrow('100');

    await bar.expectFilterSuggestion('amount', 'gt');
    expect(await bar.hasFilterSuggestion('period', 'after')).toBe(false);

    // Escape both clears the input and closes the popover, so the next test starts from a bare bar.
    await bar.pressInNarrow('Escape');
  });

  // Picking a field and thinking better of it used to leave an empty pill that filters nothing and
  // can only be got rid of by finding its remove button. Focus is the half only a browser can
  // answer: the pill and its editor are gone, so without help focus falls to the document body and
  // the next keystroke goes nowhere.
  test('abandoning a field pick drops its pill and leaves the caret in the bar', async () => {
    await bar.addField('counterparties');
    await bar.expectPillVisible('counterparties');

    await bar.dismissEditor();

    await bar.expectNoPill('counterparties');
    expect(await bar.focusedFieldTestId()).toBe('pill-narrow-input');
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // The add menu has had arrow-key navigation since `a542339f41` but nothing ever exercised it,
  // and it is the entry point to every other filter: unreachable here means unreachable full stop.
  test('a field can be picked from the add menu with the keyboard', async () => {
    await bar.openAddMenu();
    // The menu focuses its search on mount, so typing narrows without clicking into it.
    expect(await bar.focusedFieldTestId()).toBe('pill-menu-search');
    await bar.typeFocused('proto');
    await bar.pressFocused('Enter');

    // Picking a field opens its editor, so the checklist is what has focus now.
    await bar.expectPillVisible('counterparties');
    await bar.selectValue('curve');
    await bar.closeEditor('counterparties');

    await expectRows(2);
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // Escape had to reach the surrounding menu to close a checklist editor, which only worked while
  // that menu held focus — so what Escape did depended on which editor was open. The list now owns
  // it and tells the bar to close, the same as the range and text editors already did.
  test('escape alone closes a checklist editor', async () => {
    await bar.addField('counterparties');
    await bar.selectValue('curve');

    // No fallback click: Escape is the whole gesture, and what was ticked stays ticked.
    await bar.dismissEditor();
    await bar.expectEditorClosed();

    await bar.expectPillVisible('counterparties');
    await expectRows(2);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('counterparties=curve');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // Both bounds and the operator chips, without a mouse. Moving between min and max relies on
  // plain Tab, and nothing asserted the chips could be reached or toggled at all.
  test('the range editor and its operator chips work from the keyboard', async () => {
    await bar.addField('amount');
    // The editor focuses its first bound itself: `autofocus` is ignored for an input added to an
    // already-loaded document, which is why this is worth pinning.
    await bar.expectFocusedField('range-min');

    await bar.typeFocused('10');
    await bar.pressFocused('Tab');
    await bar.expectFocusedField('range-max');
    await bar.typeFocused('100');
    await bar.pressFocused('Enter');

    // Only the 20 DAI event sits between the two bounds.
    await expectRows(1);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('minAmount=10');
    expect(url()).toContain('maxAmount=100');

    // The chips sit above the bounds, so shift-tab out of the first one reaches the last chip.
    await bar.openPillEditor('amount');
    await bar.expectFocusedField('range-min');
    await bar.pressFocused('Shift+Tab');
    await bar.expectFocusedField('op-lt');
    await bar.pressFocused('Enter');

    // "less than" keeps only the upper bound, so the lower one must leave the URL with it.
    await expect.poll(() => url(), { timeout: 10000 }).not.toContain('minAmount=');
    expect(url()).toContain('maxAmount=100');
    expect(await bar.pillText('amount')).toContain('less than');

    await bar.dismissEditor();
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // A pill used to be unreachable by keyboard entirely: its root was a div with a click handler,
  // so Tab skipped straight past it and an existing filter could not be reopened without a mouse.
  // Only a real browser can answer this — jsdom does not model tab order, and asserting that the
  // element is a `<button>` in a unit test is not the same claim.
  test('an existing pill can be reached and reopened from the keyboard', async () => {
    await bar.addField('counterparties');
    await bar.selectValue('uniswap-v2', 'uniswap');
    await bar.closeEditor('counterparties');

    // The pills sit before the input in the DOM, so shift-tabbing out of it walks back into the
    // last pill: its remove control first, then the region that opens the editor.
    await bar.focusNarrowInput();
    await bar.pressFocused('Shift+Tab');
    expect(await bar.focusedTestId()).toBe('filter-pill-remove');

    await bar.pressFocused('Shift+Tab');
    expect(await bar.focusedTestId()).toBe('filter-pill-open');

    // Enter on the focused pill has to open the same editor a click does.
    await bar.pressFocused('Enter');
    await expect(ctx.sharedPage.locator('[data-testid=value-select-search]')).toBeVisible({ timeout: 10000 });

    await bar.closeEditor('counterparties');
    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // Driven entirely from the keyboard. Every bug this bar has had was a focus bug that only
  // shows up in a real browser: a menu stealing focus after the first keystroke, or `autofocus`
  // being ignored on an input added to a loaded document. Clicking rows cannot catch either.
  test('a suggestion can be highlighted and applied from the keyboard', async () => {
    await bar.narrow('Optimism');
    await bar.expectValueSuggestion('location', 'optimism');

    // The caret has to still be in the bar's input for this to reach the list at all.
    await bar.pressInNarrow('ArrowDown');
    await bar.pressInNarrow('Enter');

    await bar.expectPillVisible('location');
    await expectRows(1);

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('a checklist value can be ticked from the keyboard', async () => {
    await bar.addField('location');
    // Focus belongs to the checklist's own search box once the editor opens. The search is
    // narrowed to a single option on purpose: arrowing down wraps back onto it, so the row that
    // gets ticked is the one intended rather than whichever the list happened to order second.
    await bar.searchValues('Optimism');
    await bar.toggleHighlightedValue();
    await bar.closeEditor('location');

    await expectRows(1);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('location=optimism');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('unticking one value leaves the rest of the pill in place', async () => {
    await bar.addField('counterparties');
    await bar.selectValue('uniswap-v2', 'uniswap');
    await bar.selectValue('curve');
    await bar.closeEditor('counterparties');
    await expectRows(4);

    // Unticking is not the same as removing the pill: the other value must survive.
    await bar.openPillEditor('counterparties');
    await bar.selectValue('curve');
    await bar.closeEditor('counterparties');

    await bar.expectPillVisible('counterparties');
    await expectRows(2);
    await expect.poll(() => url(), { timeout: 10000 }).toContain('counterparties=uniswap-v2');
    expect(url()).not.toContain('curve');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  // A pill shows an icon per value up to ICON_VALUE_CAP (2) and collapses the rest to "+N", so
  // the count appears from the third value on. Asserted at the boundary: two values must NOT
  // collapse, or a cap regression in either direction passes unnoticed.
  test('a pill collapses values past the icon cap', async () => {
    await bar.addField('counterparties');
    for (const [value, search] of [
      ['uniswap-v2', 'uniswap'],
      ['curve', 'curve'],
    ])
      await bar.selectValue(value, search);
    await bar.closeEditor('counterparties');

    expect(await bar.pillValue('counterparties')).not.toContain('+');

    await bar.openPillEditor('counterparties');
    await bar.selectValue('aave-v3', 'aave');
    await bar.closeEditor('counterparties');

    expect(await bar.pillValue('counterparties')).toContain('+1');

    await bar.clearAll();
    await expectRows(TOTAL_SEEDED_EVENTS);
  });

  test('a filter matching nothing shows the empty state and can be cleared from it', async () => {
    await bar.addField('notesSubstring');
    await bar.typeTextValue('nothing matches this');
    await bar.closeEditor();

    await expectRows(0);
    const clear = ctx.sharedPage.getByRole('button', { name: 'Clear filters' });
    await expect(clear).toBeVisible();

    // The empty state's own escape hatch has to actually empty the bar.
    await clear.click();
    await bar.expectNoPill('notesSubstring');
    await expectRows(TOTAL_SEEDED_EVENTS);
  });
});

/**
 * Pagination and sort live in their own user: 24 events would swamp every row count above.
 *
 * These cover the seam between the bar and `useServerTable` — a filter has to reset the page,
 * and has to survive a sort. Date is the only column the events table sorts by.
 */
test.describe.serial('history events pill filter paging', () => {
  let ctx: SharedTestContext;
  let page: HistoryEventsPage;
  let bar: PillFilterBar;

  async function expectRows(count: number): Promise<void> {
    await expect.poll(async () => ctx.sharedPage.locator(ROW).count(), { timeout: 15000 }).toBe(count);
  }

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { formLogin: true });

    for (const event of pagedEvents())
      await apiAddOnlineEvent(request, event);

    page = new HistoryEventsPage(ctx.sharedPage);
    bar = new PillFilterBar(ctx.sharedPage);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('a full page is capped at the page size', async () => {
    await page.visit();
    await bar.waitForVisible();

    await expectRows(PAGE_SIZE);
    // The header is the only place the unpaged total appears.
    expect(await bar.pageRange()).toContain(String(PAGED_TOTAL));
  });

  test('applying a filter from a later page returns to the first', async () => {
    await bar.nextPage();
    await expect.poll(async () => bar.pageRange(), { timeout: 10000 }).toContain('11-20');

    await bar.addField('location');
    await bar.selectValue('kraken');
    await bar.closeEditor('location');

    // Without a page reset the filtered rows would sit on a page that no longer exists.
    await expectRows(PAGED_KRAKEN);
    expect(await bar.pageRange()).toContain(`1-${PAGED_KRAKEN}`);
  });

  test('a filter survives sorting by date', async () => {
    // Newest first by default, so the last kraken event leads.
    const firstNote = async (): Promise<string | null> =>
      ctx.sharedPage.locator(ROW).first().locator('[data-testid=event-notes]').textContent();
    expect(await firstNote()).toContain(`paged ${PAGED_KRAKEN - 1}`);

    await bar.toggleDateSort();

    // The sort has to actually reverse the rows, or this test would pass on a dead button.
    await expect.poll(firstNote, { timeout: 10000 }).toContain('paged 0');
    // And the filter has to still be applied on the other side of it.
    await bar.expectPillVisible('location');
    await expectRows(PAGED_KRAKEN);
    expect(ctx.sharedPage.url()).toContain('location=kraken');
  });
});

/**
 * The same symbol on two chains, which is the case the asset pill's icon, caption and chain
 * badge exist for. Its own user, so the extra optimism event cannot shift the location counts
 * in the main set.
 */
test.describe.serial('history events pill filter across chains', () => {
  let ctx: SharedTestContext;
  let page: HistoryEventsPage;
  let bar: PillFilterBar;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, {
      seed: (username) => {
        for (const [txHash, chainId] of Object.entries(multiChainChainIds))
          seedEvmTransaction(username, txHash, chainId);
      },
    });

    for (const event of multiChainEvents)
      await apiAddEvmEvent(request, event);

    page = new HistoryEventsPage(ctx.sharedPage);
    bar = new PillFilterBar(ctx.sharedPage);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('two assets sharing a symbol are filtered apart', async () => {
    await page.visit();
    await bar.waitForVisible();
    await expect.poll(async () => ctx.sharedPage.locator(ROW).count(), { timeout: 15000 }).toBe(2);

    // Driven through the URL rather than the asset picker: which USDC the remote search ranks
    // first is not ours to predict (the picker's own async path is covered elsewhere). What
    // matters here is that two assets showing the identical symbol select different rows — a
    // mix-up no assertion based on the symbol text could ever reveal.
    for (const [identifier, expected] of [
      [A_USDC_OPTIMISM, 'usdc optimism'],
      [A_USDC, 'usdc mainnet'],
    ]) {
      await ctx.sharedPage.goto(`/#/history/events?asset=${encodeURIComponent(identifier)}`);
      await bar.waitForVisible();
      await bar.expectPillVisible('asset');

      await expect.poll(async () => ctx.sharedPage.locator(ROW).count(), { timeout: 15000 }).toBe(1);
      await expect(ctx.sharedPage.locator(ROW).first().locator('[data-testid=event-notes]'))
        .toContainText(expected);
      // Both pills read "USDC", so the label alone cannot tell which is applied.
      expect(await bar.pillValue('asset')).toContain('USDC');
    }
  });
});
