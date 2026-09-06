import cron from "node-cron";
import { query } from "../database/pool.js";

export const startBackgroundSchedulers = (): void => {
  console.log("[Scheduler] Initializing background cron jobs...");

  cron.schedule("*/30 * * * *", async () => {
    try {
      const res = await query("DELETE FROM otps WHERE expiry_time < NOW()");
      console.log(`[Scheduler] Cleaned up ${res.rowCount} expired OTP verification records.`);
    } catch (e) {
      console.error("[Scheduler] Failed to clean up expired OTPs:", e);
    }
  });

  cron.schedule("0 */6 * * *", async () => {
    try {
      await query(
        `UPDATE job_sources 
         SET is_active = true 
         WHERE name IN ('linkedin', 'linkedin_posts', 'telegram', 'naukri', 'serper_jobs')`
      );
      console.log("[Scheduler] Verified and refreshed active job discovery sources.");
    } catch (e) {
      console.error("[Scheduler] Failed to refresh job sources:", e);
    }
  });
};
