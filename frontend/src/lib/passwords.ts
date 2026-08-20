/** Mots-clé et expressions de déverrouillage configurables via l'environnement.
 *  Ne contient aucun mot de passe en clair dans le dépôt public.
 */

export function getPasswords(): string[] {
  const envWords = import.meta.env.VITE_ORION_UNLOCK_WORDS || "";
  const localWords = typeof localStorage !== "undefined" ? localStorage.getItem("ORION_UNLOCK_WORDS") || "" : "";
  const combined = (envWords + "," + localWords)
    .split(",")
    .map((w) => w.trim().toLowerCase())
    .filter(Boolean);

  return Array.from(new Set(combined));
}

export function normalizePwd(s: string): string {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function isPasswordMatch(input: string): boolean {
  const norm = normalizePwd(input);
  if (!norm) return false;
  const validPasswords = getPasswords();
  if (validPasswords.length === 0) return true; // Aucun mot de passe exigé si non configuré
  return validPasswords.some((pwd) => norm === pwd || norm.includes(pwd));
}
