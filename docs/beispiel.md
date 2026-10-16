---
title: MD Viewer – Beispieldokument
autor: tikogaming1
version: 1.0.0
tags:
  - markdown
  - beispiel
  - test
---

# MD Viewer – Beispieldokument

Dieses Dokument zeigt alles, was MD Viewer darstellen kann. Öffnen Sie es nach der
Installation mit **`md-viewer beispiel.md`** oder über *Datei → Öffnen* (Strg+O).

> [!NOTE]
> Der YAML-Block ganz oben heißt **Frontmatter** und wird hier eingeklappt angezeigt –
> genau wie auf GitHub.

## Textgestaltung

Ein Absatz mit **fett**, *kursiv*, ***fett und kursiv***, `Inline-Code`,
~~durchgestrichen~~, [einem Link](https://github.com/tikogaming1/md-viewer) und einem
Autolink: https://example.com

Ein zweiter Absatz für den Zeilenumbruch-Test
– dieser Satz steht in der Quelle in der nächsten Zeile.

Hochgestellt: x^2^, tiefgestellt: H~2~O, mathematisch: $e^{i\pi} + 1 = 0$.

### Listen

- Ein Punkt
- Noch ein Punkt
  - Unterpunkt
  - Noch einer
- Dritter Punkt

1. Erstens
2. Zweitens
3. Drittens

Aufgabenliste:

- [x] Markdown rendern
- [x] Inhaltsverzeichnis erzeugen
- [ ] Eigene Wünsche ergänzen

### Zitate und Hinweis-Blöcke

> Ein klassisches Zitat.
>
> — mit zweiter Zeile und Quellenangabe

> [!TIP]
> Tipp-Blöcke eignen sich für Empfehlungen.

> [!IMPORTANT]
> Wichtige Hinweise werden farbig hervorgehoben.

> [!WARNING]
> Warnungen fallen auf.

> [!CAUTION]
> Und Vorsicht-Hinweise erst recht.

## Tabellen

| Funktion | Kurztaste | Anmerkung |
| --- | :---: | ---: |
| Datei öffnen | `Strg+O` | mehrere Tabs möglich |
| Im Dokument suchen | `Strg+F` | Treffer werden gezählt |
| Inhaltsverzeichnis | `Strg+B` | linke Seitenleiste |
| Als HTML exportieren | `Strg+E` | eigenständige Datei |
| Drucken | `Strg+P` | falls WebKitGTK es kann |

## Codeblöcke

```python
#!/usr/bin/env python3
"""Kleine Demo: Primzahlen bis 50."""

def primzahlen(limit: int) -> list[int]:
    gefunden = []
    for kandidat in range(2, limit + 1):
        if all(kandidat % teiler for teiler in range(2, int(kandidat ** 0.5) + 1)):
            gefunden.append(kandidat)
    return gefunden


if __name__ == "__main__":
    print(primzahlen(50))
```

```bash
# Paket bauen und installieren
make deb
sudo apt install ./release/md-viewer_1.0.0_all.deb
md-viewer ~/Notizen/README.md
```

```javascript
const parser = new DOMParser();
const doc = parser.parseFromString(markdown, 'text/html');
console.log(`Überschriften: ${doc.querySelectorAll('h1, h2, h3').length}`);
```

```json
{
  "theme": "auto",
  "zoom": 100,
  "toc_visible": true
}
```

```sql
SELECT titel, geaendert
FROM notizen
WHERE tags LIKE '%markdown%'
ORDER BY geaendert DESC
LIMIT 10;
```

Ein Codeblock ohne Sprachangabe (wird nicht geraten):

```
kein highlighting, nur Text
```

## Mathematik

Inline: Die Kreisfläche ist $A = \pi r^2$, der Satz des Pythagoras lautet $a^2 + b^2 = c^2$.

Als eigener Block:

$$
\int_0^\infty e^{-x^2}\,\mathrm{d}x = \frac{\sqrt{\pi}}{2}
$$

$$
\begin{pmatrix} a & b \\ c & d \end{pmatrix}
\begin{pmatrix} x \\ y \end{pmatrix}
=
\begin{pmatrix} ax + by \\ cx + dy \end{pmatrix}
$$

## Bilder

Relativ zum Dokument (wird aus demselben Ordner geladen):

![Das Logo von MD Viewer](bild.png)

Externes Bild (per Klick groß, wenn „Externe Bilder blockieren“ aktiv ist):

![GitHub-Markenzeichen](https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png)

## Aufklappbarer Bereich

<details>
<summary>Hier klicken zum Aufklappen</summary>

Versteckter Inhalt mit **Markdown** funktioniert nur eingeschränkt – rohes HTML wird
aus Sicherheitsgründen gefiltert, der Text bleibt aber erhalten.

</details>

## Fußnoten

Markdown unterstützt Fußnoten.[^quelle] Auch mehrere sind möglich.[^zwei]

[^quelle]: Die Fußnote erscheint am Ende des Dokuments mit Rückverweis.

[^zwei]: Zweite Fußnote.

## Verweise auf andere Dateien

- [Zweites Beispieldokument](verweise.md) – öffnet sich im Viewer
- [Zurück zum Anfang](#md-viewer--beispieldokument) – springt im Dokument
- [Projektseite](https://github.com/tikogaming1/md-viewer) – öffnet den Browser

---

### Tiefere Überschrift (Ebene 3)

#### Und noch tiefer (Ebene 4)

##### Ebene 5

###### Ebene 6

Das Inhaltsverzeichnis links zeigt alle Ebenen – beim Scrollen wird der aktuelle
Abschnitt hervorgehoben.

#### Lange Liste für das Scrollen

1. Eintrag eins
2. Eintrag zwei
3. Eintrag drei
4. Eintrag vier
5. Eintrag fünf
6. Eintrag sechs
7. Eintrag sieben
8. Eintrag acht
9. Eintrag neun
10. Eintrag zehn
11. Eintrag elf
12. Eintrag zwölf
13. Eintrag dreizehn
14. Eintrag vierzehn
15. Eintrag fünfzehn
16. Eintrag sechzehn
17. Eintrag siebzehn
18. Eintrag achtzehn
19. Eintrag neunzehn
20. Eintrag zwanzig

**Ende des Beispieldokuments.**
