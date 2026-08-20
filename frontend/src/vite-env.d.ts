/// <reference types="vite/client" />

/**
 * Déclaration des variables d'environnement lues côté client.
 *
 * Sans ce fichier, `import.meta.env` est inconnu de TypeScript et la
 * compilation échoue sur passwords.ts.
 *
 * ⚠ Tout ce qui porte le préfixe VITE_ est embarqué EN CLAIR dans le bundle
 * livré au navigateur. Ces mots de déverrouillage protègent l'ouverture de
 * l'interface, ils ne constituent pas un secret serveur — le vrai contrôle
 * d'accès reste ORION_SECRET_TOKEN, côté serveur.
 */
interface ImportMetaEnv {
  /** Mots de déverrouillage de l'interface, séparés par des virgules. */
  readonly VITE_ORION_UNLOCK_WORDS?: string;
  /** Token serveur pour un deploiement web maitrise. */
  readonly VITE_ORION_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
