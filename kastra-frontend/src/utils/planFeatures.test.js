import { describe, expect, it } from "vitest";
import {
  hasFeature,
  PLAN_LABELS,
  SIDEBAR_FEATURE,
  UNLOCK_PLAN,
} from "./planFeatures";

// Cheapest → most expensive. Feature access must only ever grow along this axis.
const PLAN_LADDER = ["free", "starter", "business", "premium"];

describe("hasFeature", () => {
  it("locks everything gated on the free plan", () => {
    for (const feature of Object.keys(UNLOCK_PLAN)) {
      expect(hasFeature("free", feature), `${feature} on free`).toBe(false);
    }
  });

  it("unlocks the paid features on premium", () => {
    for (const feature of Object.keys(UNLOCK_PLAN)) {
      expect(hasFeature("premium", feature), `${feature} on premium`).toBe(true);
    }
  });

  it("treats an unknown plan as locked rather than throwing", () => {
    expect(hasFeature("enterprise", "reports")).toBe(false);
    expect(hasFeature(undefined, "reports")).toBe(false);
    expect(hasFeature(null, "reports")).toBe(false);
  });

  it("treats an unknown feature as locked", () => {
    expect(hasFeature("premium", "time_travel")).toBe(false);
  });
});

describe("plan ladder", () => {
  it("never revokes a feature when you upgrade", () => {
    for (const feature of Object.keys(UNLOCK_PLAN)) {
      let seenUnlocked = false;
      for (const plan of PLAN_LADDER) {
        const allowed = hasFeature(plan, feature);
        if (seenUnlocked) {
          expect(allowed, `${feature} regressed at ${plan}`).toBe(true);
        }
        if (allowed) seenUnlocked = true;
      }
    }
  });

  it("unlocks each feature exactly at its advertised plan", () => {
    for (const [feature, unlockPlan] of Object.entries(UNLOCK_PLAN)) {
      const unlockIndex = PLAN_LADDER.indexOf(unlockPlan);
      expect(unlockIndex, `${feature} names an unknown plan`).toBeGreaterThan(-1);

      PLAN_LADDER.forEach((plan, i) => {
        expect(hasFeature(plan, feature), `${feature} on ${plan}`).toBe(i >= unlockIndex);
      });
    }
  });
});

describe("sidebar gating", () => {
  it("maps every gated route to a feature that has an unlock plan", () => {
    for (const [path, feature] of Object.entries(SIDEBAR_FEATURE)) {
      expect(UNLOCK_PLAN[feature], `${path} → ${feature}`).toBeDefined();
    }
  });

  it("uses absolute paths so the lookup matches the router", () => {
    for (const path of Object.keys(SIDEBAR_FEATURE)) {
      expect(path.startsWith("/"), path).toBe(true);
    }
  });
});

describe("PLAN_LABELS", () => {
  it("labels every plan on the ladder", () => {
    for (const plan of PLAN_LADDER) {
      expect(PLAN_LABELS[plan], plan).toBeTruthy();
    }
  });
});
