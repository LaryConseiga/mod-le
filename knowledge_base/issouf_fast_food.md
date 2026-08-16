# ISSOUF FAST FOOD — Base de connaissance

> Fichier source pour l'ingestion RAG (menu, horaires, informations pratiques).
> Format : chaque plat est un bloc `###` distinct → un plat = un chunk = un embedding.
> Chaque plat porte un `id` stable, à réutiliser comme `menu_item_id` côté commande (Feuille A-08 de l'architecture).
>
> ⚠️ Plusieurs points sont marqués **À CONFIRMER** — ce sont des ambiguïtés du fichier source, pas des suppositions silencieuses. Merci de les trancher avant l'ingestion en base.

## Informations pratiques

- Nom : Issouf Fast Food
- Adresse : À COMPLÉTER
- Téléphone : +226 67 33 69 74
- Moyens de paiement acceptés : Orange Money ou espèces (cash) — le paiement Orange Money se fait sur le même numéro, +226 67 33 69 74
- Récupération ou livraison : le client choisit entre venir récupérer sa commande sur place ou se faire livrer
- Délai de préparation : environ 20 minutes après validation de la commande
- Devise : XOF (Franc CFA, zone BCEAO)
- Sucrerie : ce terme désigne nos sodas — Coca Cola, Pepsi et 7UP, à 500 FCFA chacun

## Horaires d'ouverture

Ouvert 24h/24, 7j/7 (tous les jours, sans exception).

---

## Menu

### 🍔 Hamburgers

#### Hamburger simple
- id: hamburger-simple
- Catégorie : Hamburgers
- Composition : Steak, frites, légumes
- Prix : 800 FCFA / 1000 FCFA — **À CONFIRMER** : les deux prix correspondent à quoi (taille, avec/sans supplément) ?

#### Cheeseburger
- id: cheeseburger
- Catégorie : Hamburgers
- Composition : Steak, frites, légumes, fromage, ketchup, mayonnaise
- Prix : 1000 FCFA

#### Double cheeseburger
- id: double-cheeseburger
- Catégorie : Hamburgers
- Composition : Double steak, frites, légumes, double fromage, ketchup, mayonnaise
- Prix : 1500 FCFA

#### Hamburger Royal
- id: hamburger-royal
- Catégorie : Hamburgers
- Composition : Steak, frites, légumes, ketchup, mayonnaise, œuf, saucisson
- Prix : 1000 FCFA / 1500 FCFA — **À CONFIRMER** (même remarque que Hamburger simple)

#### Hamburger Gourmand
- id: hamburger-gourmand
- Catégorie : Hamburgers
- Composition : Double steak, frites, légumes, double fromage, ketchup, mayonnaise, œuf, saucisson
- Prix : 2000 FCFA

### 🥙 Kebabs

#### Kebab simple
- id: kebab-simple
- Catégorie : Kebabs
- Composition : Viande hachée, ketchup, mayonnaise
- Prix : 1000 FCFA

#### Kebab gourmand
- id: kebab-gourmand
- Catégorie : Kebabs
- Composition : Viande hachée, ketchup, mayonnaise, fromage, saucisson
- Prix : 1500 FCFA

### 🥖 Pain anglais

> ⚠️ **À CONFIRMER** : le fichier source liste quatre lignes "Pain anglais" à des prix différents (600 / 700 / 800 FCFA) sans nom distinctif pour les trois premières. J'ai gardé l'ordre du fichier et ajouté un identifiant provisoire — il faudra les renommer (tailles ? recettes différentes ?) avant l'ingestion.

#### Pain anglais simple
- id: pain-anglais-simple
- Catégorie : Pain anglais
- Composition : Viande hachée, ketchup, mayonnaise, saucisson
- Prix : 600 FCFA

#### Pain anglais (variante 2) — nom à préciser
- id: pain-anglais-2
- Catégorie : Pain anglais
- Composition : Viande hachée, ketchup, mayonnaise, saucisson
- Prix : 700 FCFA

#### Pain anglais (variante 3) — nom à préciser
- id: pain-anglais-3
- Catégorie : Pain anglais
- Composition : Viande hachée, ketchup, mayonnaise, saucisson
- Prix : 800 FCFA

#### Pain anglais fromage
- id: pain-anglais-fromage
- Catégorie : Pain anglais
- Composition : Viande hachée, ketchup, mayonnaise, saucisson, fromage
- Prix : 1000 FCFA

### 🍲 Plats sautés

#### Rognon + frites
- id: rognon-frites
- Catégorie : Plats sautés
- Prix : 1500 FCFA / 2000 FCFA — **À CONFIRMER** (portion demi/entière ?)

#### ½ poulet sauté + frites
- id: demi-poulet-saute-frites
- Catégorie : Plats sautés
- Prix : 2500 FCFA / 3000 FCFA — **À CONFIRMER**

### 🍟 Friture

#### Saucisse grillée épicée + frites
- id: saucisse-grillee-frites
- Catégorie : Friture
- Prix : 2000 FCFA

#### Saucisse grillée épicée seule
- id: saucisse-grillee-seule
- Catégorie : Friture
- Prix : 1500 FCFA

#### Poulet pané + frites
- id: poulet-pane-frites
- Catégorie : Friture
- Prix : 2500 FCFA

#### Poulet pané
- id: poulet-pane
- Catégorie : Friture
- Prix : 2000 FCFA

#### Frites
- id: frites
- Catégorie : Friture
- Prix : 1000 FCFA

#### Alloco
- id: alloco
- Catégorie : Friture
- Prix : 1000 FCFA

### 🌯 Chawarma viande

#### Chawarma viande mini
- id: chawarma-viande-mini
- Catégorie : Chawarma viande
- Composition : Frites, légumes, ketchup, mayonnaise — **À CONFIRMER** : pas de viande listée dans la composition du "mini", est-ce voulu ?
- Prix : 1000 FCFA

#### Chawarma viande maxi
- id: chawarma-viande-maxi
- Catégorie : Chawarma viande
- Composition : Viande, frites, légumes, ketchup, mayonnaise
- Prix : 1500 FCFA

#### Chawarma viande gourmand
- id: chawarma-viande-gourmand
- Catégorie : Chawarma viande
- Composition : Viande, fromage, saucisson, frites, légumes, ketchup, mayonnaise
- Prix : 2000 FCFA

### 🍗 Chawarma poulet

#### Chawarma poulet mini
- id: chawarma-poulet-mini
- Catégorie : Chawarma poulet
- Composition : Frites, légumes, ketchup, mayonnaise — même remarque que ci-dessus
- Prix : 1300 FCFA

#### Chawarma poulet maxi
- id: chawarma-poulet-maxi
- Catégorie : Chawarma poulet
- Composition : Poulet, frites, légumes, ketchup, mayonnaise
- Prix : 2000 FCFA

#### Chawarma poulet gourmand
- id: chawarma-poulet-gourmand
- Catégorie : Chawarma poulet
- Composition : Poulet, fromage, saucisson, frites, légumes, ketchup, mayonnaise
- Prix : 2500 FCFA

### 🍝 Spaghetti

#### Spaghetti bolognaise (fromage)
- id: spaghetti-bolognaise-fromage
- Catégorie : Spaghetti
- Prix : 2000 FCFA

### 🍽️ Plat spécial

#### Plat spécial + frites
- id: plat-special-frites
- Catégorie : Plat spécial
- Prix : 2500 FCFA

#### Plat spécial au fromage + frites
- id: plat-special-fromage-frites
- Catégorie : Plat spécial
- Prix : 3000 FCFA

### 🥤 Boissons

#### Coca Cola
- id: coca-cola
- Catégorie : Boissons
- Prix : 500 FCFA

#### Pepsi
- id: pepsi
- Catégorie : Boissons
- Prix : 500 FCFA

#### 7UP
- id: 7up
- Catégorie : Boissons
- Prix : 500 FCFA

#### Bissap
- id: bissap
- Catégorie : Boissons
- Prix : 300 FCFA

### ☕ Boissons chaudes

#### Expresso
- id: expresso
- Catégorie : Boissons chaudes
- Prix : 300 FCFA
