# Terminal Footer Validation Report

**Date:** 2025-02-20  
**Page:** http://127.0.0.1:8080/fetch_target  
**Flow:** Navigate → (optional Load .env + Keep Existing) → Fetch Target Account Data

---

## Observed Behavior

### Successful Runs (no Load .env)
- **Footer visibility:** Footer row appears ~0.5s after fetch click, remains visible for 40+ seconds during active fetch.
- **Label text:** Always present when footer visible. Content cycles: "Fetching target... - API active", "Fetching target... - Waiting for API response (Ns)", with context (e.g. "globals/service_tokens", "projects/jobs p3/24").
- **Label width:** Constant 844px (no collapse observed).
- **Row height:** Constant 24px (h-6). No layout shifts.
- **Icon + text:** No samples with icon visible and label empty.

### Load .env + Keep Existing Flow
- Page reloads after Keep Existing (ui.navigate.reload()). Footer visibility depends on fetch timing post-reload; in some runs footer was never observed (fetch may complete before sampling or credentials/session differ).

### High-Frequency Sampling (80ms for 15s)
- 180 visible samples, 0 with empty label.
- No transient "icon without text" states captured.

---

## Reproduction Notes

1. **Without Load .env:** Use existing session credentials; click "Fetch Target Account Data" directly. Footer appears and stays visible during fetch.
2. **With Load .env:** Click Load .env → Keep Existing → wait for reload → Fetch. Reload clears context; ensure fetch is triggered after page stabilizes.
3. **Bug not reproduced:** Automated runs did not capture the reported "spinner only, no text" or "twitchy" behavior.

---

## Likely UI Causes (from Code Analysis)

### 1. Label Collapse (Most Likely)
- Footer label: `w-full overflow-hidden text-ellipsis whitespace-nowrap` (terminal_output.py:275–276).
- In a flex row, `w-full` without `min-width` can collapse to 0 when the parent is constrained.
- Icon has `flex-shrink-0`, so it stays visible; label can disappear if it gets 0 width.
- **Fix:** Add `min-w-0` (flex shrink) and/or `min-w-[120px]` so the label keeps a minimum width.

### 2. Visibility/Text Update Race
- `_set_activity_text()` and `_set_activity_visibility()` are called together in `set_activity()`.
- `_update_activity_indicator` runs every 1s and calls `_set_activity_text()` with new strings.
- NiceGUI updates are async (WebSocket). Brief moments of empty text are possible if:
  - `set_text("")` is called before the new value, or
  - The DOM update is delayed while the row is shown.
- **Fix:** Avoid clearing text; always set the new value in one update.

### 3. Row Toggle Twitch
- Row toggles via `classes(remove="hidden")` / `classes(add="hidden")`.
- Rapid show/hide (e.g. at fetch start/end) can cause visible flicker.
- **Fix:** Use `visibility: hidden` or `opacity: 0` instead of `display: none` for smoother transitions, or debounce visibility changes.

### 4. Scroll Area / Overflow
- Footer is inside the terminal card; scroll area has `height: calc(500px - 50px)`.
- If the scroll container layout changes during log streaming, the footer row could be clipped or resized.
- **Fix:** Ensure footer has a fixed height (`h-6`) and is outside the scroll area, or give the scroll container a stable height.

---

## Element Details

| Element | Classes | Role |
|--------|---------|------|
| Footer row | `w-full h-6 min-h-6 max-h-6 items-center gap-2 px-3 border-t border-slate-800 overflow-hidden hidden` | Container; `hidden` toggled for visibility |
| Icon | `text-cyan-400 animate-spin text-sm flex-shrink-0` | Spinner; never shrinks |
| Label | `text-xs text-cyan-300 font-mono whitespace-nowrap overflow-hidden text-ellipsis w-full` | Status text; can collapse with `w-full` in flex |

---

## Recommended Next Steps

1. Add `min-w-0` and `min-w-[120px]` to the footer label to prevent collapse.
2. Ensure `_set_activity_text()` never sets empty string when the row is visible.
3. Test on a smaller viewport (e.g. 800px width) to see if label collapse appears.
4. Add a test that asserts footer label has non-empty text whenever the footer row is visible.
