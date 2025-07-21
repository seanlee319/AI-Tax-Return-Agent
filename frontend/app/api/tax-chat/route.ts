import { OpenAI } from 'openai';
import { NextResponse } from 'next/server';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const TAX_PROMPT = `You are a tax assistant that ONLY answers US tax questions. 
If asked about other topics, respond: "I specialize in US taxes. Ask about W-2s, 1099s, deductions, or filing."

Current tax year: 2024
Key rules:
- Standard deduction: $14,600 (single), $29,200 (married)
- Child tax credit: $2,000 per child
Keep responses under 100 words.`;

interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface RequestBody {
  message: string;
  chatHistory: ChatMessage[];
}

export async function POST(req: Request) {
  const { message, chatHistory }: RequestBody = await req.json();

  try {
    const response = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [
        { role: 'system', content: TAX_PROMPT },
        ...chatHistory.map((msg: ChatMessage) => ({
          role: msg.role,
          content: msg.content.length > 200 
            ? msg.content.substring(0, 200) + '...' 
            : msg.content
        })),
        { role: 'user', content: message }
      ],
      temperature: 0.2,
      max_tokens: 150,
    });

    const reply = response.choices[0]?.message?.content || "Please ask your tax question again.";
    return NextResponse.json({ reply });

  } catch (error) {
    console.error('OpenAI error:', error);
    return NextResponse.json(
      { reply: "Our tax service is currently unavailable. Please try again later." },
      { status: 200 }
    );
  }
}