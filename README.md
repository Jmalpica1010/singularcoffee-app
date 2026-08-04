# SingularCoffee

The public face of SingularCoffee, an Android app for specialty coffee: the
landing page, the recipe catalogue, and the place to report things.

- **`recipes.json`** — the catalogue the app refreshes from.
- **`docs/`** — the page published at
  <https://jmalpica1010.github.io/singularcoffee-app/>.
- **Issues** — a missing scale, a bug, or a recipe.

The source of the app lives in `singularcoffee-dev`, which is private. Nothing
here needs it: everything in this repository is meant to be read without an
account, which is the whole reason the two are separate.

## The catalogue

The app ships a copy of this file inside the APK, so it works from the first
launch and with no connection. When there is network it refreshes from here, so
a recipe added to this repository reaches every phone without shipping a new
version of the app.

The file the app reads is **`recipes.json`** on the default branch. It has to
stay reachable without authentication — that is the whole reason this repository
is separate and public.

## Adding a recipe

**From the app:** open the recipe and tap contribute. It opens an issue here with
the entry already formatted. A maintainer adds the **`receta aprobada`** label and
a workflow validates it, appends it to `recipes.json`, commits, and closes the
issue. Nobody edits JSON by hand.

The label is the gate on purpose. This file is downloaded into everyone's app, so
merging whatever an anonymous account posts would be letting a stranger write into
other people's phones. The robot does the mechanical part; the approval stays
human.

**No GitHub account?** Share the recipe from the app as a file — it goes over
whatever you already use, and whoever receives it reads it with
Settings → Backup → Import. Send it to a maintainer and they can put it here.

**By hand:** append an object to `recipes` and open a pull request. `scripts/` will
check it:

```bash
python3 -c "import sys;sys.path.insert(0,'scripts');
from catalogue import load,validate_catalogue;print(validate_catalogue(load('recipes.json')))"
```

### Bringing a new brewing method

A recipe can carry the method it was designed for, so someone can contribute a
recipe for a brewer the app has never heard of. Add an optional `brewer` object;
the app creates it on import if the phone does not have it, matching by name and
brand, and never touches one that already exists — that one may be tuned to its
owner's taste.

```json
"brewer": {
  "name": "Origami S",
  "brand": "Origami",
  "style": "POUR_OVER",
  "geometry": "CONICAL",
  "filterMaterial": "ABACA",
  "capacityMl": 400,
  "defaultRatio": 16.0,
  "defaultTempC": 92.0
}
```

`style` is one of `POUR_OVER`, `IMMERSION`, `HYBRID`, `COLD_BREW`, `ESPRESSO`,
`OTHER`. `geometry` one of `CONICAL`, `FLAT_BOTTOM`, `WAVE`, `CYLINDRICAL`,
`BASKET`, `OTHER`. `filterMaterial` one of `PAPER_BLEACHED`, `PAPER_NATURAL`,
`ABACA`, `CLOTH`, `METAL`, `NONE`. A value the app does not know is not fatal — it
falls back to `OTHER` — but then the method arrives badly described, so the
validator rejects it rather than letting it through quietly.

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
