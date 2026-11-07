# Costumbres del hospital

Dos situaciones que ninguna norma escrita cubre y que casi todos los operadores resuelven igual.
Ambas se derivaron de `historial/historial.csv`; el código que las verifica está en
`curado/costumbres.py` y la clasificación completa la produce `curado/clasificar.py`.

## Costumbre 1 — Aviso al voluntariado con 75 años o más y sin acompañante

**Se avisa al voluntariado cuando el paciente tiene 75 años o más y no tiene acompañante.
En cualquier otra situación no se avisa.**

Ninguna de las 20 secciones de las normas menciona al voluntariado. El Servicio Social de
NOR-COB-03 §3 es otro circuito: depende de la cobertura, no de la edad, y es el único aviso que
las normas regulan.

El corte está exactamente en 75 años, no en los 67 del parámetro P-ADM-2 que usan NOR-ADM-02 y el
resto de las normas de admisión. Entre los operadores que siguen la costumbre, el salto es
limpio:

| Edad | Filas sin acompañante | Con aviso |
|---|---|---|
| 70 a 74 | 70 | 0 |
| 75 a 80 | 69 | 69 |

**Evidencia.** 17 de los 20 operadores la cumplen sin una sola excepción: **0 desviaciones en
1674 filas**. Las 151 filas que se apartan son todas de tres operadores — OP-11 (60), OP-17 (53)
y OP-04 (38) —, que avisan al voluntariado también fuera de esa situación.

- La cumplen avisando: `H-0013`, `H-0016`, `H-0036`, `H-0044`, `H-0045`, `H-0063`
- La cumplen no avisando, por tener 73 o 74 años: `H-0041`, `H-0161`, `H-0206`, `H-0250`
- La cumplen no avisando, por tener acompañante pese a superar los 75: `H-0023`, `H-0075`, `H-0082`, `H-0083`
- Se apartan: `H-0005` (OP-04, 35 años), `H-0006` (OP-17, 48), `H-0009` (OP-17, 60), `H-0053` (OP-04, 70), `H-0056` (OP-17, 62)

## Costumbre 2 — Con dos credenciales se verifica la prepaga

**Cuando el paciente presenta una credencial de obra social y otra de prepaga, se verifica la
afiliación de la prepaga.**

NOR-COB-02 §2 manda verificar la afiliación con el nombre de la entidad y el número de afiliado,
pero no dice cuál cuando hay más de una credencial. NOR-COB-01 §4 tampoco: solo dice que la
credencial reemplaza la consulta.

**Evidencia.** De las 193 filas con dos credenciales, en **184 (95,3%)** se verificó la prepaga.
La elección no depende del orden en que figuran: la prepaga estaba primera en 105 casos y segunda
en 88, y se la verificó igual.

- La cumplen: `H-0010`, `H-0011`, `H-0021`, `H-0052`, `H-0056`, `H-0075`
- Se apartan, las nueve: `H-0334`, `H-0404`, `H-0408`, `H-0480`, `H-0792`, `H-0881`, `H-1190`, `H-1467`, `H-1520`

Las nueve son de los mismos tres operadores que rompen la costumbre 1: OP-17 (4), OP-11 (4) y
OP-04 (1).

## Lo que no es una costumbre

El `plazo_circuito_min` aparece en el historial con dos valores por circuito más dos variantes
cinco minutos menores (sepsis 15 y 60, pero también 10 y 55; ECG y ACV 10, pero también 5). No es
una costumbre: lo fija **NOR-TDE-04 §1**, que descuenta los minutos del parámetro P-TDE-5 cuando
el paciente llegó en ambulancia. Las 97 filas que no respetan ese descuento son errores, no ruido.
