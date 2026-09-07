---
name: minimal-diff
description: Réduire un diff aux modifications nécessaires à la demande en retirant les refactorings, reformattages et retouches quasi cosmétiques sans rapport. À utiliser seulement en fin d'implémentation pour nettoyer un changement existant sans en élargir la portée.
---

# Minimal Diff

Comprendre brièvement l'objectif avant de réduire le diff des ajouts : lire la demande, inspecter l'état des fichiers modifiés, le diff complet et le code d'origine dans son contexte. Identifier le comportement attendu et les conventions locales afin de distinguer une modification nécessaire d'une simple préférence de style.

Il faut bien vérifier le diff complet, y compris git staged et unstaged, afin d'avoir un diff final une fois fusionné dans le staged qui sera moindre. Ne pas stager, laisser l'utilisateur stager lui-même les changements retenus pour le diff minimal.

Réduire et centraliser le code ajouté, on préfère faire des suppressions si c'est pour des améliorations dans ce sens.

- Conserver chaque changement requis pour le comportement, les tests associés, la documentation affectée et les artefacts générés attendus par le projet.
- Retirer les reformattages, changements d'espaces ou de fins de ligne, réordonnancements, renommages, corrections de commentaires et substitutions syntaxiques sans lien avec l'objectif.
- Rétablir les littéraux extraits dans une variable, constante, fonction, type ou wrapper utilisé une seule fois lorsque cette abstraction n'apporte rien au changement. La conserver si elle documente utilement le domaine, centralise une valeur par défaut ou de configuration avec ses pairs, satisfait une contrainte technique, ou améliore nettement la compréhension.
- Écarter les helpers à usage unique, annotations de types redondantes, guards spéculatifs et généralisations préparant un besoin futur lorsqu'ils ne sont pas nécessaires à la modification demandée.
- Ne pas mélanger une modification fonctionnelle avec un refactoring, un déplacement de code, une migration ou un nettoyage global indépendant. Si un déplacement est requis, garder autant que possible le contenu déplacé inchangé.
- Limiter les changements de dépendances, fichiers de verrouillage, configuration, snapshots et fichiers générés à ceux effectivement produits ou exigés par la modification.
- Respecter le style du code environnant. Ne pas minimiser le nombre de lignes au prix de la lisibilité, de la correction, de la sécurité ou de la maintenabilité.
