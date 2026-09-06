import { env } from "../config/env.js";

export interface ChatCompletionOptions {
  prompt: string;
  systemInstruction?: string;
  temperature?: number;
  maxTokens?: number;
}

export const generateAIResponse = async (options: ChatCompletionOptions): Promise<string> => {
  const { prompt, systemInstruction, temperature = 0.7, maxTokens = 1024 } = options;

  if (env.GROQ_API_KEY) {
    try {
      const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GROQ_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "llama-3.3-70b-versatile",
          messages: [
            ...(systemInstruction ? [{ role: "system", content: systemInstruction }] : []),
            { role: "user", content: prompt },
          ],
          temperature,
          max_tokens: maxTokens,
        }),
      });
      if (res.ok) {
        const data: any = await res.json();
        return data.choices?.[0]?.message?.content || "";
      }
    } catch (e) {
      console.warn("[AI Gateway] Groq failed, attempting fallback:", e);
    }
  }

  if (env.OPENAI_API_KEY) {
    try {
      const res = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.OPENAI_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: [
            ...(systemInstruction ? [{ role: "system", content: systemInstruction }] : []),
            { role: "user", content: prompt },
          ],
          temperature,
          max_tokens: maxTokens,
        }),
      });
      if (res.ok) {
        const data: any = await res.json();
        return data.choices?.[0]?.message?.content || "";
      }
    } catch (e) {
      console.warn("[AI Gateway] OpenAI failed:", e);
    }
  }

  return "VidyaMarg AI Career Mentor: Career intelligence graph is active. How may I guide your career journey today?";
};
