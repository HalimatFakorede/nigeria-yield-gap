# Notes

Things that went wrong and what fixed them. Three of these changed a number.

---

**Encoding.** Read the FAOSTAT file as latin-1 at first. It does not throw an error, it
just turns `Côte d'Ivoire` into `CÃ´te d'Ivoire`, so every join on that country silently
dropped it. Now utf-8, with a check in `load_faostat` that stops if accented names come
through wrong.

**World Bank aggregates.** I was filtering them out with `iso3.str.len() == 3`, which does
not work because `WLD` and `SSF` are three letters. About 20% of the regression panel was
World, Euro area and similar, which also double count the countries inside them. Now I use
the World Bank's own country list. Moved the elasticity about 4%.

**Baseline too weak.** My gradient boosting model scored 0.72 against each country's own
average at 0.49, which looked good. Holding each country at its last known yield scores
0.88 and beats it. Added a lagged yield to the model, which gets it to 0.887. Barely
ahead.

**Argument order.** A function returned `(-240, -57, -297)` instead of `(40, -15, 25)`
because the parameters were declared in a different order to how I called it. Both
hectares and tonnes are floats so nothing complained. Now I test new functions on a case
where I already know the answer.

**Year column stayed as text.** `panel["year"].between(1990, 2023)` raised a TypeError
because I reran an earlier cell without rerunning the one that converted the type. The
conversion now happens in `faostat_to_long` so it cannot be skipped.

**Windows setup.** `python --version` opened the Microsoft Store instead of reporting a
version, which means Python is shadowed by an app execution alias, not missing. Turned
off the aliases in Settings. Also had to run
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` before the venv
would activate.
