# mod-le

Agent WhatsApp pour Issouf Fast Food — Flask, Groq, Supabase (Postgres + pgvector).

## Ingestion RAG (menu, horaires, infos pratiques)

1. Créer un projet [Supabase](https://supabase.com) et exécuter [db/schema.sql](db/schema.sql) dans son éditeur SQL (crée l'extension `pgvector` et toutes les tables).
2. Copier `.env.example` en `.env` et renseigner `SUPABASE_DB_URL` (Project Settings > Database > Connection string).
3. Installer les dépendances :
   ```
   pip install -r requirements.txt
   ```
4. Éditer [knowledge_base/issouf_fast_food.md](knowledge_base/issouf_fast_food.md) si besoin, puis lancer l'ingestion :
   ```
   python -m ingestion.ingest
   ```
5. Vérifier avec une recherche réelle :
   ```
   python -m ingestion.search "vous êtes ouverts jusqu'à quelle heure ?"
   python -m ingestion.search "c'est combien le cheeseburger ?"
   ```

Relancer `python -m ingestion.ingest` à chaque modification du fichier `.md` — les lignes existantes sont mises à jour (upsert par `id`), pas dupliquées.