---
name: better-unit-tests
description: Écrire, nettoyer ou améliorer des tests automatisés durables, notamment les tests unitaires générés avec une IA. À utiliser pour ajouter, retirer, corriger ou réviser des tests.
---

# Better Unit Tests

Inspecter d'abord les meilleurs tests et outils de test existants.

- Préférer des tests rapides au niveau acceptation via une API publique minimale. Réserver les tests unitaires étroits aux règles isolées (parseurs, expressions régulières) ou à la demande explicite.
- Décrire les données et résultats avec le vocabulaire métier. Vérifier le comportement observable, jamais les détails d'implémentation.
- Éviter les mocks excessifs. Isoler uniquement les vrais services externes avec des doublures réutilisables.
- Imiter les bons exemples et réutiliser fixtures, builders, helpers et API de test. S'il n'existe aucun modèle, créer d'abord un test représentatif et l'infrastructure minimale.
- Viser un filet anti-régression : un refactoring sans changement de comportement ne doit pas casser les tests.
- Retirer les tests cosmétiques qui ne vérifient pas le comportement attendu.
- Ne pas tester les détails d'implémentation, les messages d'erreur ou les traces de log.
- Ne pas se baser sur des valeurs arbitraires, toujours utiliser des données représentatives et génériques.
- Anonymiser les données sensibles et éviter les informations personnelles dans les tests.
- Ne pas tester les autres langues que la langue par défaut, sauf si c'est le but du test.
- Ne pas tester les niveaux déjà testés implicitement. Analyser tous les tests existants avant d'ajouter un nouveau test pour éviter la redondance. Les tests ont pour but de vérifier les comportements précis, pas de vérifier des choses évidentes ou déjà naturellement/implicitement couvertes par d'autres tests.
