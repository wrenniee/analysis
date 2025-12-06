# How to Replicate the "Yield Farm & Moonshot" Strategy

This guide breaks down the exact steps to mimic the trader "Annica" based on their historical and current market behavior.

## Phase 1: The "Iron Fortress" (Early Week / Low Volatility)
**Goal:** Build a bankroll and secure safe yields by betting against extreme outcomes.
**Timing:** Days 1-3 of the market (e.g., Friday - Monday).

### Step 1: Identify the "Impossible" Zones
Look at the market distribution. Identify the buckets that seem highly unlikely to hit.
*   **Low End:** `0-19`, `20-39`, ... up to `100-119`.
*   **High End:** `500+`, `480-499` (If sentiment is neutral/bearish).

### Step 2: Execute "Buy No" Orders (Yield Farming)
Place Limit Orders to **Buy "No"** in these zones.
*   **Price Target:** 99.0¢ - 99.8¢.
*   **Yield:** 0.2% - 1.0% return on capital.
*   **Volume:** High. This is where you park the majority of your capital (e.g., $5,000+).
*   **Logic:** You are acting as the "House". You are selling lottery tickets to people betting on extreme outcomes.

### Step 3: The "Mid-Curve" Short
*   **Target:** `300-339` (or whatever the "unlikely middle" is).
*   **Action:** Buy "No" at ~90¢ - 92¢.
*   **Yield:** ~8% - 10%.
*   **Risk:** Higher. Only do this if you have a strong view that the count will be higher/lower than this specific range.

---

## Phase 2: The Pivot (Mid-Week / Catalyst)
**Goal:** Switch from "House" to "Gambler" using the profits from Phase 1.
**Timing:** Mid-week or when a catalyst appears (e.g., Elon starts tweeting aggressively).

### Step 1: Close the "High" Shorts
*   **Action:** Sell your "No" shares on the High Buckets (`480+`, `500+`).
*   **Why?** If the tweet count starts rising, these "No" shares will drop in value. You want to exit with your small profit or break-even before the crowd rushes in.

### Step 2: Accumulate "Yes" (The Moonshot)
*   **Target:** The High Buckets you just exited (`460-479`, `480-499`).
*   **Action:** Aggressively **Buy "Yes"**.
*   **Price Target:** 0.3¢ - 2.0¢.
*   **Sizing:** Use the profits from Phase 1 + a portion of your principal.
*   **Logic:** You are now betting on the "Black Swan" event.

---

## Summary Checklist

| Phase | Action | Buckets | Order Type | Price Target |
| :--- | :--- | :--- | :--- | :--- |
| **1. Early** | **Buy No** | Low (`20-119`) | Limit | 99.5¢+ |
| **1. Early** | **Buy No** | High (`500+`) | Limit | 99.0¢+ |
| **2. Pivot** | **Sell No** | High (`500+`) | Market/Limit | Exit |
| **2. Pivot** | **Buy Yes** | High (`460+`) | Limit/Market | < 2.0¢ |

## Automation Logic
See `mimic_bot_logic.py` for the Python implementation of this specific workflow.
