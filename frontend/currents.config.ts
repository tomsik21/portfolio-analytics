import { CurrentsConfig } from "@currents/playwright";

// Project ID identifies which Currents.dev project results upload to —
// safe to commit (it's not a secret, just an identifier).
//
// Record Key IS a secret — it's read from an environment variable, never
// hardcoded here. Locally, export CURRENTS_RECORD_KEY yourself if you
// want local runs to upload too (optional — CI always uploads). In CI,
// it comes from the CURRENTS_RECORD_KEY GitHub Actions secret.
const config: CurrentsConfig = {
  recordKey: process.env.CURRENTS_RECORD_KEY,
  projectId: process.env.CURRENTS_PROJECT_ID || "REPLACE_WITH_YOUR_PROJECT_ID",
};

export default config;
