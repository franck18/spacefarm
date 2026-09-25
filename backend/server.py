"""Configure et démarre le serveur SpaceFarm."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import threading

import db
from routes import Handler


def main():
    # Lire les options de lancement.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8000, type=int)
    parser.add_argument('--static', default=str(Path(__file__).resolve().parent.parent / 'frontend' / 'dist'))
    parser.add_argument('--db', default=os.environ.get('SPACEFARM_DB', '/var/lib/spacefarm/spacefarm.db'),
                        help='Fichier SQLite des relevés.')
    parser.add_argument('--token', default=os.environ.get('SPACEFARM_TOKEN', ''),
                        help='Jeton partagé exigé des capteurs. Vide = aucune authentification.')
    parser.add_argument('--stale', default=120, type=int,
                        help='Secondes au-delà desquelles une mesure est déclarée indisponible.')
    parser.add_argument('--retention', default=7, type=int, help='Jours de relevés conservés.')
    parser.add_argument('--history-hours', default=6, type=float, help='Fenêtre du graphique.')
    parser.add_argument('--reservoir', default=0.729, type=float, help='Capacité du réservoir en litres (729 mL).')
    args = parser.parse_args()

    config = {'db': args.db, 'token': args.token, 'stale': args.stale,
              'retention': args.retention, 'history_hours': args.history_hours,
              'reservoir': args.reservoir}

    # Préparer la base et son entretien automatique.
    db.initialise(args.db)
    db.record_event(args.db, 'success', 'Service SpaceFarm démarré sur le Raspberry Pi')
    threading.Thread(target=db.purge_loop, args=(config,), daemon=True).start()

    # Écouter les requêtes de la Yún et des navigateurs.
    server = ThreadingHTTPServer((args.host, args.port),
                                 partial(Handler, static_dir=args.static, config=config))
    print('SpaceFarm disponible sur http://{}:{}'.format(args.host, args.port), flush=True)
    print('Base de données : {}{}'.format(args.db, '' if args.token else ' · ingestion sans jeton'),
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
