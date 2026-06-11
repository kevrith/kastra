// Feature availability per plan — mirrors backend plan_limits.py
const FEATURES = {
  free:     { expenses: false, products: false, suppliers: false, recurring: false, reports: false, audit_logs: false, paystack: false, client_portal: false, sms: false, etims: false, ai: false, global_search: false },
  starter:  { expenses: true,  products: true,  suppliers: true,  recurring: false, reports: true,  audit_logs: false, paystack: true,  client_portal: true,  sms: false, etims: false, ai: true,  global_search: true  },
  business: { expenses: true,  products: true,  suppliers: true,  recurring: true,  reports: true,  audit_logs: true,  paystack: true,  client_portal: true,  sms: true,  etims: true,  ai: true,  global_search: true  },
  premium:  { expenses: true,  products: true,  suppliers: true,  recurring: true,  reports: true,  audit_logs: true,  paystack: true,  client_portal: true,  sms: true,  etims: true,  ai: true,  global_search: true  },
};

export function hasFeature(plan, feature) {
  return FEATURES[plan]?.[feature] ?? false;
}

// Which plan first unlocks a feature
export const UNLOCK_PLAN = {
  expenses:      "starter",
  products:      "starter",
  suppliers:     "starter",
  reports:       "starter",
  client_portal: "starter",
  paystack:      "starter",
  ai:            "starter",
  global_search: "starter",
  recurring:     "business",
  audit_logs:    "business",
  sms:           "business",
  etims:         "business",
};

export const PLAN_LABELS = {
  free:     "Free",
  starter:  "Starter",
  business: "Business",
  premium:  "Premium",
};

// Sidebar path → feature key
export const SIDEBAR_FEATURE = {
  "/expenses":  "expenses",
  "/products":  "products",
  "/suppliers": "suppliers",
  "/recurring": "recurring",
  "/reports":   "reports",
  "/audit-log": "audit_logs",
};
