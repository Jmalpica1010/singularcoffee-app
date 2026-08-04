"""Validación del catálogo de recetas.

Este archivo lo descarga la app de todo el mundo. Una entrada mal formada no da
un error visible: `RecipeCatalog.parse` descarta la receta rota en silencio para
no tumbar el resto, así que el síntoma es «me falta una receta» sin nada que lo
explique. Y un `id` repetido es peor, porque la app empareja por `id` y dos
entradas con el mismo se pisan entre teléfonos.

De ahí que esto corra en dos sitios: al fusionar una aportación y en cada push
del repositorio. Sin dependencias externas a propósito, para que funcione en
cualquier runner sin instalar nada.
"""

from __future__ import annotations

import json
import re

# Los tipos de paso que entiende la app. Tienen que coincidir con PourKind.
POURING = {"BLOOM", "POUR", "PULSE", "BYPASS"}
NON_POURING = {"SWIRL", "STIR", "DRAWDOWN"}
KINDS = POURING | NON_POURING

# Y los del método. Copiados de `data/model/Enums.kt`, no deducidos: al
# adivinarlos, este validador aceptaba «CONE» —que no existe— y rechazaba
# «CONICAL», «WAVE» y «ABACA», que son los reales. Un valor que la app no conoce
# no rompe nada, cae a OTHER, pero entonces el método llega mal descrito y nadie
# se enteraría.
STYLES = {"POUR_OVER", "IMMERSION", "HYBRID", "COLD_BREW", "ESPRESSO", "OTHER"}
GEOMETRIES = {"CONICAL", "FLAT_BOTTOM", "WAVE", "CYLINDRICAL", "BASKET", "OTHER"}
FILTERS = {"PAPER_BLEACHED", "PAPER_NATURAL", "ABACA", "CLOTH", "METAL", "NONE"}

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Topes de longitud. No son estética: el nombre va en una tarjeta de 1080 px y en
# una fila de lista, y un texto sin freno la rompe en el teléfono de otro.
MAX_NAME = 60
MAX_INSTRUCTION = 160
MAX_DESCRIPTION = 400


class Invalid(Exception):
    """Una entrada que no puede entrar al catálogo, con el motivo."""


def _text(value, field: str, where: str, limit: int, required: bool = True) -> str:
    if not isinstance(value, dict):
        raise Invalid(f"{where}: falta el objeto de texto")
    # `en` siempre: es el respaldo cuando el idioma activo no está, y sin él la
    # receta desaparece para quien tenga la app en inglés.
    for language in ("es", "en"):
        if language not in value:
            raise Invalid(f"{where}: falta el texto en «{language}»")
    for language in ("es", "en"):
        text = value[language]
        if not isinstance(text, str):
            raise Invalid(f"{where}: el texto en «{language}» no es una cadena")
        if required and not text.strip():
            raise Invalid(f"{where}: el texto en «{language}» está vacío")
        if len(text) > limit:
            raise Invalid(f"{where}: «{language}» pasa de {limit} caracteres ({len(text)})")
    return value["es"]


def _number(value, field: str, where: str, low: float, high: float):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise Invalid(f"{where}: «{field}» tiene que ser un número")
    if not low <= value <= high:
        raise Invalid(f"{where}: «{field}» = {value} fuera de [{low}, {high}]")
    return float(value)


def validate_brewer(brewer, where: str) -> None:
    if not isinstance(brewer, dict):
        raise Invalid(f"{where}: «brewer» tiene que ser un objeto")
    name = brewer.get("name")
    if not isinstance(name, str) or not name.strip():
        raise Invalid(f"{where}: el método necesita nombre")
    if len(name) > MAX_NAME:
        raise Invalid(f"{where}: el nombre del método pasa de {MAX_NAME} caracteres")
    for field, allowed in (
        ("style", STYLES),
        ("geometry", GEOMETRIES),
        ("filterMaterial", FILTERS),
    ):
        if field in brewer and brewer[field] not in allowed:
            raise Invalid(f"{where}: «{field}» = {brewer[field]!r} no es válido")
    if "defaultRatio" in brewer:
        _number(brewer["defaultRatio"], "defaultRatio", where, 1, 40)
    if "defaultTempC" in brewer:
        _number(brewer["defaultTempC"], "defaultTempC", where, 1, 100)
    if "capacityMl" in brewer:
        _number(brewer["capacityMl"], "capacityMl", where, 1, 5000)


def validate_recipe(recipe, where: str | None = None) -> str:
    """Comprueba una entrada y devuelve su `id`."""
    if not isinstance(recipe, dict):
        raise Invalid("la receta no es un objeto")

    identifier = recipe.get("id")
    if not isinstance(identifier, str) or not ID_PATTERN.match(identifier):
        raise Invalid(
            f"«id» = {identifier!r} no vale: minúsculas, dígitos y guiones, "
            "sin guiones al principio ni al final"
        )
    where = where or f"receta «{identifier}»"

    author = recipe.get("author")
    if not isinstance(author, str) or not author.strip():
        # Sin autor la receta no es de nadie, y acreditarlo es lo que sostiene
        # el catálogo: es la única moneda que cobra quien aporta.
        raise Invalid(f"{where}: falta «author»")

    _number(recipe.get("doseGrams"), "doseGrams", where, 1, 200)
    _number(recipe.get("ratio"), "ratio", where, 1, 40)
    _number(recipe.get("waterTempC"), "waterTempC", where, 1, 100)

    text = recipe.get("text")
    if not isinstance(text, dict):
        raise Invalid(f"{where}: falta «text»")
    for language in ("es", "en"):
        body = text.get(language)
        if not isinstance(body, dict):
            raise Invalid(f"{where}: falta «text.{language}»")
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            raise Invalid(f"{where}: falta el nombre en «{language}»")
        if len(name) > MAX_NAME:
            raise Invalid(f"{where}: el nombre en «{language}» pasa de {MAX_NAME}")
        description = body.get("description", "")
        if not isinstance(description, str) or len(description) > MAX_DESCRIPTION:
            raise Invalid(f"{where}: la descripción en «{language}» pasa de {MAX_DESCRIPTION}")

    if "brewer" in recipe:
        validate_brewer(recipe["brewer"], where)

    steps = recipe.get("steps")
    if not isinstance(steps, list) or not steps:
        raise Invalid(f"{where}: hace falta al menos un paso")

    last_second = -1
    pours = []
    for index, step in enumerate(steps, start=1):
        place = f"{where}, paso {index}"
        if not isinstance(step, dict):
            raise Invalid(f"{place}: no es un objeto")

        kind = step.get("kind")
        if kind not in KINDS:
            raise Invalid(f"{place}: «kind» = {kind!r} no existe. Válidos: {sorted(KINDS)}")

        second = step.get("atSecond", 0)
        _number(second, "atSecond", place, 0, 3600)
        # El tiempo no puede retroceder: la guía los recorre en orden y un salto
        # hacia atrás deja al usuario leyendo un paso que ya pasó.
        if second < last_second:
            raise Invalid(f"{place}: «atSecond» = {second} va antes del paso anterior")
        last_second = second

        _text(step.get("text"), "text", place, MAX_INSTRUCTION)

        if kind in POURING:
            multiple = step.get("doseMultiple")
            fraction = step.get("targetFraction")
            if multiple is not None:
                _number(multiple, "doseMultiple", place, 0.1, 20)
            elif fraction is not None:
                _number(fraction, "targetFraction", place, 0.01, 1)
            else:
                # Un vertido sin objetivo no se puede completar: la guía va por
                # peso y se quedaría esperando para siempre.
                raise Invalid(f"{place}: un vertido necesita «targetFraction» o «doseMultiple»")
            pours.append(step)

    if not pours:
        raise Invalid(f"{where}: no hay ningún paso que añada agua")

    # El último vertido tiene que llegar al total, o la receta acaba antes de
    # haber servido la taza entera.
    final = pours[-1]
    if final.get("doseMultiple") is None and final.get("targetFraction") != 1:
        raise Invalid(
            f"{where}: el último vertido llega a {final.get('targetFraction')!r} y no a 1"
        )

    return identifier


def validate_catalogue(data) -> list[str]:
    """Comprueba el archivo entero. Devuelve los `id` en orden."""
    if not isinstance(data, dict):
        raise Invalid("el catálogo no es un objeto")
    recipes = data.get("recipes")
    if not isinstance(recipes, list):
        raise Invalid("falta el array «recipes»")

    seen: dict[str, int] = {}
    for position, recipe in enumerate(recipes, start=1):
        identifier = validate_recipe(recipe)
        if identifier in seen:
            raise Invalid(
                f"«{identifier}» está dos veces (posiciones {seen[identifier]} y {position}). "
                "La app empareja por id: dos entradas iguales se pisan."
            )
        seen[identifier] = position
    return list(seen)


def load(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
