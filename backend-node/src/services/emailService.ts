import { env } from "../config/env.js";

export const sendOtpEmail = async (email: string, code: string): Promise<boolean> => {
  const htmlContent = `
    <!DOCTYPE html>
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px;">
          <h2 style="color: #4f46e5; margin-top: 0;">VidyaMarg AI</h2>
          <p>Hello,</p>
          <p>We received a request to reset your VidyaMarg AI account password.</p>
          <div style="text-align: center; margin: 25px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #4f46e5; background: #eef2ff; padding: 10px 24px; border-radius: 6px;">${code}</span>
          </div>
          <p style="color: #6b7280; font-size: 14px;">This code will expire in 10 minutes.</p>
          <p>If you did not request this, please ignore this message.</p>
        </div>
      </body>
    </html>
  `;

  if (env.RESEND_API_KEY) {
    try {
      const res = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.RESEND_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          from: `VidyaMarg AI <${env.SMTP_FROM_EMAIL.endsWith("@gmail.com") ? "onboarding@resend.dev" : env.SMTP_FROM_EMAIL}>`,
          to: [email],
          subject: "Password Reset Verification Code - VidyaMarg AI",
          html: htmlContent,
        }),
      });
      if (res.ok) {
        console.log(`[Email] Successfully sent OTP via Resend API to ${email}`);
        return true;
      }
    } catch (e) {
      console.warn("[Email] Resend API error, continuing to fallback:", e);
    }
  }

  console.log(`[Dev Fallback Email] OTP for ${email}: ${code}`);
  return true;
};
