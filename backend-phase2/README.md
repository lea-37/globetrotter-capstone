# Bastos Explorer — Phase 2 : Microservices

Le monolithe de `backend/` est décomposé en **trois services indépendants**
plus une **passerelle API (API Gateway)**, chacun avec ses propres données,
son propre process, et son propre port.

```
                         ┌──────────────────┐
                         │   API Gateway     │  :5000  (point d'entrée unique)
                         └───────┬───────────┘
              ┌──────────────────┼───────────────────┐
              ▼                  ▼                    ▼
   ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
   │  User Service     │ │  Place Service   │ │  Review Service  │
   │  :5001            │ │  :5002           │ │  :5003           │
   │  users.json       │ │  places.json     │ │  reviews.json    │
   └──────────────────┘ └──────────────────┘ └────────┬─────────┘
                                  ▲                     │
                                  └── appel REST sync ───┘
                              (vérifie qu'un lieu existe
                               avant d'accepter un avis)
```

## Les trois services

| Service | Rôle | Données possédées |
|---|---|---|
| **user-service** (`:5001`) | Inscription, connexion, émission des jetons JWT | `users.json` |
| **place-service** (`:5002`) | Recherche et détail des lieux de Bastos, catégories | `places.json` |
| **review-service** (`:5003`) | Avis et notes | `reviews.json` |
| **api-gateway** (`:5000`) | Point d'entrée unique pour le frontend ; authentifie, route, et **compose** les réponses qui touchent plusieurs services (ex. la fiche d'un lieu = place-service + review-service) | — |

## Communication inter-services

- **Synchrone (REST)** — quand quelqu'un poste un avis, `review-service`
  appelle `place-service` (`GET /internal/places/<id>/exists`) pour
  vérifier que le lieu existe réellement avant d'accepter l'avis, plutôt
  que de faire confiance à l'identifiant envoyé par le client.
- **Agrégation à la passerelle** — `api-gateway` appelle `review-service`
  (`GET /reviews/summary?place_ids=...`) en un seul lot pour attacher la
  note moyenne et le nombre d'avis à toute une page de résultats, plutôt
  que d'interroger `review-service` une fois par lieu.
- **Sécurité "zero trust"** — chaque service vérifie lui-même la
  signature du jeton JWT (secret partagé `BASTOS_SECRET_KEY`) au lieu de
  supposer qu'une requête qui l'atteint a forcément déjà été validée par
  la passerelle. Un appel direct à `review-service` avec un jeton invalide
  est refusé, même en contournant la passerelle.

## Lancer en local (sans Docker)

Ouvrez 4 terminaux :

```bash
cd user-service   && pip install -r requirements.txt && PORT=5001 python3 app.py
cd place-service  && pip install -r requirements.txt && PORT=5002 python3 app.py
cd review-service && pip install -r requirements.txt && PORT=5003 python3 app.py
cd api-gateway    && pip install -r requirements.txt && PORT=5000 python3 app.py
```

Vérifiez que tout est connecté :
```bash
curl http://127.0.0.1:5000/health
```
La réponse liste l'état de chacun des trois services en aval.

## Lancer avec Docker Compose

```bash
cd backend-phase2
docker compose up --build
```

Les quatre services démarrent, chacun dans son conteneur, sur les mêmes
ports (5000–5003). Les données JSON sont montées en volume pour persister
entre redémarrages.

## Frontend

Le frontend ne change pas : `frontend/js/config.js` pointe déjà sur
`http://127.0.0.1:5000` (la passerelle), qui expose exactement les mêmes
routes `/api/...` que le monolithe de Phase 1.
