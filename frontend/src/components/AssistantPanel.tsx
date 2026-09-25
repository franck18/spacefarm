// Permet de connecter l’assistant et de demander une analyse.
import { useEffect, useState } from 'react';
import { MessageSquare } from 'lucide-react';

type Status = {
  connected: boolean;
  login?: { verificationUrl: string; userCode: string } | null;
  loginError?: string | null;
};

export default function AssistantPanel() {
  const [code, setCode] = useState(() => sessionStorage.getItem('spacefarm-assistant-code') ?? '');
  const [unlocked, setUnlocked] = useState(false);
  const [status, setStatus] = useState<Status>({ connected: false });
  const [question, setQuestion] = useState(
    'Analyse les dernières mesures et indique les points à surveiller.',
  );
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

  async function request(action: string, payload = {}) {
    const response = await fetch(`${base}/api/assistant/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-SpaceFarm-Code': code },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(115000),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error ?? 'Assistant indisponible.');
    return result;
  }

  async function action(name: string) {
    setBusy(true);
    setError('');
    try {
      const result = await request(name, name === 'ask' ? { question } : {});
      if (name === 'ask') setAnswer(result.answer);
      else {
        setStatus(result);
        setUnlocked(true);
        sessionStorage.setItem('spacefarm-assistant-code', code);
      }
      if (name === 'logout') setAnswer('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Connexion impossible.');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!unlocked || !status.login || status.connected) return;
    const timer = setInterval(() => {
      void request('status')
        .then(setStatus)
        .catch((e) => setError(String(e.message)));
    }, 4000);
    return () => clearInterval(timer);
  }, [unlocked, status.login, status.connected, code]);

  const loginUrl = status.login?.verificationUrl;
  const safeUrl = loginUrl?.startsWith('https://auth.openai.com/') ? loginUrl : undefined;
  return (
    <section id="assistant" className="panel assistant-panel">
      <div className="panel-heading">
        <h2>
          <MessageSquare size={18} /> Assistant SpaceFarm
        </h2>
        <span>{status.connected ? 'ChatGPT connecté' : 'Connexion ChatGPT'}</span>
      </div>
      <p className="caption">
        Analyse des mesures via Codex · Conseils uniquement · Le PC doit rester allumé.
      </p>
      {!unlocked ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void action('status');
          }}
          className="assistant-form"
        >
          <label htmlFor="assistant-code">Code d’accès SpaceFarm</label>
          <input
            id="assistant-code"
            type="password"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            autoComplete="off"
            required
          />
          <button className="text-button" disabled={busy || !code}>
            Ouvrir l’assistant
          </button>
        </form>
      ) : !status.connected ? (
        <div className="assistant-form">
          <button
            className="text-button"
            disabled={busy || !!status.login}
            onClick={() => void action('login')}
          >
            Se connecter avec ChatGPT
          </button>
          {status.login && (
            <div role="status">
              <p>Sur la page officielle OpenAI, saisis ce code :</p>
              <strong className="assistant-device-code">{status.login.userCode}</strong>
              {safeUrl && (
                <p>
                  <a href={safeUrl} target="_blank" rel="noopener noreferrer">
                    Ouvrir la connexion OpenAI ↗
                  </a>
                </p>
              )}
              <p className="caption">
                En attente de ta connexion… Si demandé, active la connexion par code d’appareil dans
                les paramètres de sécurité de ChatGPT.
              </p>
            </div>
          )}
        </div>
      ) : (
        <form
          className="assistant-form"
          onSubmit={(e) => {
            e.preventDefault();
            void action('ask');
          }}
        >
          <label htmlFor="assistant-question">Ta question sur la culture</label>
          <textarea
            id="assistant-question"
            value={question}
            maxLength={2000}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
          />
          <p className="caption">
            En lançant l’analyse, les dernières mesures et ta question sont envoyées à OpenAI. Les
            limites de ton compte s’appliquent.
          </p>
          <div className="assistant-actions">
            <button className="text-button" disabled={busy || !question.trim()}>
              {busy ? 'Analyse en cours…' : 'Analyser les mesures'}
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => void action('logout')}
            >
              Déconnecter ChatGPT
            </button>
          </div>
        </form>
      )}
      {(error || status.loginError) && (
        <p role="alert" className="amber">
          {error || status.loginError}
        </p>
      )}
      {answer && (
        <div className="assistant-answer" aria-live="polite">
          {answer}
        </div>
      )}
    </section>
  );
}
