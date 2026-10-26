# Engineering lessons

## A schema boundary is useful but not a physics contract

`SimulationInput` catches missing module/inverter references before work begins. It does not enforce every physical range, timestep or geometry invariant. Reference validity and model validity need different evidence.

## Put the provider seam outside the model

The offline fixture replaces weather retrieval while leaving pvlib execution intact. This makes an integration example possible without pretending synthetic weather qualifies PVGIS or a real site's yield. It also makes the distinction between a model run and a provider test visible.

## Name the quantity, units and loss boundary together

Annual energy, monthly energy, instantaneous power and mean power are not interchangeable. Here the extra losses affect only the annual branch. A chart with tidy labels can still conceal incompatible quantities; the branch diagram exposes that contract failure without changing the model.

## Diagnostics are not independent proof

The tree recomputes an approximate story from percentages; project grid energy is then assigned from annual output. Agreement in an assigned value is not a conservation check. Likewise, a PDF header and nonzero size establish artifact creation, not chart accuracy or visual quality.

## UI affordances need an implementation map

Some controls only store state. Typed domain objects coexist with the flat active dictionary, and conversion is partial. A polished screen must not imply that shadow tracing, battery dispatch or automatic string wiring exists. Keeping an explicit inactive-controls inventory is more honest than expanding the feature list.

## Reproducibility has layers

A working existing environment, a buildable wheel, an installed wheel, a clean locked dependency installation and a live provider workflow are separate results. Preserve each result's scope instead of using one to stand in for the others.
