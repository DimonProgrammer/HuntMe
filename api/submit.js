export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const data = req.body;
  const token = process.env.BOT_TOKEN;
  const chatId = process.env.ADMIN_CHAT_ID;

  if (token && chatId) {
    const flag = data.country === 'PH' ? '🇵🇭' : data.country === 'NG' ? '🇳🇬' : '🌍';
    const lines = [
      `${flag} *New Lead — Apex Talent*`,
      `👤 ${data.name}`,
      `📱 ${data.whatsapp}`,
      `🌍 ${data.country}`,
      `🔤 English: ${data.english || '—'} | Status: ${data.status || '—'}`,
      `🎂 Age 18+: ${data.age || '—'}`,
    ];

    try {
      await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          text: lines.join('\n'),
          parse_mode: 'Markdown',
        }),
      });
    } catch (_) {
      // Telegram unreachable — still return success to user
    }
  }

  return res.status(200).json({ status: 'ok' });
}
