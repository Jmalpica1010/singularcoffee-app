"""Mete al catálogo la receta que viene en una incidencia.

La app genera la entrada JSON ya formateada y la deja en el cuerpo de la
incidencia dentro de un bloque ```json. Esto la saca, la valida y la añade a
`recipes.json`. Es el paso que faltaba: sin él, aportar una receta terminaba en
una incidencia que alguien tenía que copiar a mano, así que en la práctica no
llegaba a nadie.

**Esto no se ejecuta solo cuando alguien abre una incidencia.** Corre cuando un
mantenedor le pone la etiqueta de aprobada, y la diferencia importa: el archivo
se descarga en el teléfono de todos, así que fusionar automáticamente lo que
publique cualquiera sería dejar que un desconocido escriba en la app de los
demás. El robot hace el trabajo mecánico; el visto bueno sigue siendo humano.

Uso:
    python3 scripts/merge_contribution.py <archivo-con-el-cuerpo> [recipes.json]

Sale con 0 si añadió algo, 1 si no había nada que añadir, y 2 si la receta no es
válida. El mensaje va a la salida estándar para poder pegarlo como comentario.
"""

from __future__ import annotations

import re
import sys

from catalogue import Invalid, load, save, validate_recipe

BLOCK = re.compile(r"```json\s*(.+?)```", re.DOTALL)


def extract(body: str) -> str:
    """El bloque ```json del cuerpo. El último, si hay varios."""
    blocks = BLOCK.findall(body)
    if not blocks:
        raise Invalid(
            "No encontré un bloque ```json en la incidencia. La app lo genera "
            "sola: si se editó a mano, hay que dejar el bloque tal cual venía."
        )
    return blocks[-1].strip()


def merge(body: str, path: str) -> str:
    import json

    raw = extract(body)
    try:
        recipe = json.loads(raw)
    except json.JSONDecodeError as error:
        raise Invalid(f"El bloque no es JSON válido: {error}") from error

    # Puede venir la entrada sola o envuelta en un catálogo entero.
    if isinstance(recipe, dict) and "recipes" in recipe:
        recipes = recipe["recipes"]
        if not isinstance(recipes, list) or len(recipes) != 1:
            raise Invalid("Se esperaba una sola receta en el bloque")
        recipe = recipes[0]

    identifier = validate_recipe(recipe)

    catalogue = load(path)
    existing = {item.get("id") for item in catalogue["recipes"]}
    if identifier in existing:
        raise Invalid(
            f"«{identifier}» ya está en el catálogo. Si es una corrección, hay "
            "que editar la entrada existente: cambiarle el id la convertiría en "
            "una receta distinta y quien ya la tenga se quedaría con la vieja."
        )

    catalogue["recipes"].append(recipe)
    save(path, catalogue)

    name = recipe["text"]["es"]["name"]
    author = recipe["author"]
    method = recipe.get("brewer", {}).get("name")
    line = f"Añadida **{name}** de {author} como `{identifier}`."
    if method:
        line += f" Trae también el método **{method}**, que se creará en los teléfonos que no lo tengan."
    return line


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: merge_contribution.py <archivo-con-el-cuerpo> [recipes.json]")
        return 2
    body_path = sys.argv[1]
    catalogue_path = sys.argv[2] if len(sys.argv) > 2 else "recipes.json"

    with open(body_path, encoding="utf-8") as handle:
        body = handle.read()

    try:
        print(merge(body, catalogue_path))
    except Invalid as error:
        print(f"No pude añadirla: {error}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
