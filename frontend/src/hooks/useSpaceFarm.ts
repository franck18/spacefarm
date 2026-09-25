// Actualise les mesures et transmet les commandes de la page.
import { useCallback, useEffect, useRef, useState } from 'react';
import { provider } from '../data/provider';
import type { Command, Snapshot } from '../data/types';

export function useSpaceFarm() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [pending, setPending] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [receivedAt, setReceivedAt] = useState<number | null>(null);
  // Une seule requête à la fois : lecture ou commande.
  const busy = useRef(false);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    let canceled = false;
    const refresh = async () => {
      if (paused || busy.current) return;
      busy.current = true;
      try {
        const state = await provider.read();
        if (!canceled) {
          setData(state);
          setReceivedAt(Date.now());
          setError(null);
        }
      } catch (e) {
        if (!canceled)
          setError(e instanceof Error ? e.message : 'Connexion au service impossible.');
      } finally {
        busy.current = false;
      }
    };
    void refresh();
    // Actualiser les mesures toutes les trois secondes.
    const poll = setInterval(() => void refresh(), 3000);
    const clock = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      canceled = true;
      alive.current = false;
      clearInterval(poll);
      clearInterval(clock);
    };
  }, [paused]);

  // Utiliser l’heure du PC pour détecter une coupure, même si celle du Pi est décalée.
  const age = receivedAt === null ? 0 : Math.max(0, Math.floor((now - receivedAt) / 1000));
  const disconnected = paused || !!error || age > 10;
  const send = useCallback(
    async (command: Command) => {
      if (busy.current || disconnected) return;
      busy.current = true;
      setPending(true);
      setActionError(null);
      try {
        const state = await provider.command(command);
        if (alive.current) setData(state);
      } catch (e) {
        if (alive.current) setActionError(e instanceof Error ? e.message : 'Commande refusée.');
      } finally {
        busy.current = false;
        if (alive.current) setPending(false);
      }
    },
    [disconnected],
  );

  return {
    data,
    error,
    actionError,
    dismissError: () => setActionError(null),
    disconnected,
    age,
    pending,
    send,
    paused,
    toggleConnection: () => {
      if (provider.kind === 'mock') setPaused((p) => !p);
    },
    isMock: provider.kind === 'mock',
  };
}
