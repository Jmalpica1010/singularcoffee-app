# SingularCoffee — public

The landing page and the public recipe catalogue of SingularCoffee, an Android
app for specialty coffee. The app itself is a private repository; this one holds
what has to be readable with no account:

- **`recipes.json`** — the catalogue the app refreshes from.
- **`docs/`** — the page published at
  <https://jmalpica1010.github.io/singular-coffee/>.
- **Issues** — where a missing scale, a bug, or a recipe gets reported.

## The catalogue

The app ships a copy of this file inside the APK, so it works from the first
launch and with no connection. When there is network it refreshes from here, so
a recipe added to this repository reaches every phone without shipping a new
version of the app.

The file the app reads is **`recipes.json`** on the default branch. It has to
stay reachable without authentication — that is the whole reason this repository
is separate and public.

## Adding a recipe

Append an object to `recipes` and open a pull request.

```json
{
  "id": "author-method",
  "author": "Who designed it",
  "doseGrams": 20,
  "ratio": 15.0,
  "waterTempC": 92,
  "text": {
    "es": { "name": "…", "grindHint": "…", "description": "…" },
    "en": { "name": "…", "grindHint": "…", "description": "…" }
  },
  "steps": [
    { "kind": "BLOOM", "atSecond": 0, "doseMultiple": 2.0,
      "text": { "es": "…", "en": "…" } },
    { "kind": "POUR", "atSecond": 45, "targetFraction": 0.65,
      "text": { "es": "…", "en": "…" } }
  ]
}
```

### Fields

| Field | Meaning |
|---|---|
| `id` | Stable identifier. The app matches on it, so **never reuse or change one** — a new `id` is a new recipe. |
| `author` | Credited on the brew and on the shared image. Required in practice: a recipe without an author is nobody's. |
| `ratio` | Water as a multiple of the dose. `15.0` means 1:15. |
| `waterTempC` | Celsius. The app converts for anyone using Fahrenheit. |
| `text` | Per language. `en` is the fallback when the active language is missing, so **always include `en`**. |
| `steps` | In order. See below. |

### Steps

`kind` is one of `BLOOM`, `POUR`, `PULSE`, `BYPASS` (these add water) or
`SWIRL`, `STIR`, `DRAWDOWN` (these do not).

The distinction matters during a brew: the app drives pours by weight from the
scale, and a step that adds no water can never reach a weight target on its own.
Those are shown as an instruction in place of the running weight, and the guide
moves on by itself as soon as the scale starts climbing again — there is nothing
to press with wet hands. Getting `kind` wrong is what leaves the guide stuck.

A pour's target is either:

- `targetFraction` — cumulative weight as a fraction of the total water.
  `0.65` means "pour until the scale reads 65 % of the total".
- `doseMultiple` — cumulative weight as a multiple of the dose. Use this for a
  bloom specified as "twice the coffee": it then follows the dose instead of
  drifting when the ratio changes. Takes precedence over `targetFraction`.

`atSecond` is when the step starts, and it is guidance only — the weight is what
advances the guide. It still needs to be right, because it is what tells someone
reading the recipe how fast to work.

Steps that add no water inherit the weight of the pour before them.

## Language

Spanish and English. Text in any other language is ignored rather than shown
untranslated.
