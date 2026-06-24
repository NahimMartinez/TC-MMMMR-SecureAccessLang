# SecureAccessLang

Analizador léxico-sintáctico para SecureAccessLang, un lenguaje de dominio específico (DSL) para describir políticas de autenticación y autorización mediante definición de roles, usuarios, inicio y cierre de sesión, autenticación multifactor (MFA) y permisos de acceso.

Trabajo Integrador — Teoría de la Computación, 2026  
Universidad Nacional del Nordeste — Facultad de Ciencias Exactas y Naturales y Agrimensura  
Licenciatura en Sistemas de Información

## Integrantes

- Maidana Pablo Gastón
- Martínez Castro Gustavo Nahim
- Miño Gomez Juan Daniel
- Morales Lopez Luana Belén
- Rodríguez Antorena Milo Tahiel

---

# Estructura del proyecto

```text
.
├── lexer.py
├── parser.py
├── casos_prueba.txt
├── test_runner.py
└── README.md
```

Descripción de los archivos:

- **lexer.py**: analizador léxico implementado con PLY.
- **parser.py**: analizador sintáctico descendente recursivo LL(1), construcción del AST y recuperación de errores en modo pánico.
- **casos_prueba.txt**: conjunto de casos válidos, inválidos y parciales.
- **test_runner.py**: ejecución automática de la batería de pruebas.
- **README.md**: documentación del proyecto.

---

# Arquitectura

El proyecto está dividido en tres etapas principales:

## 1. Análisis léxico

El lexer transforma el texto fuente en una secuencia de tokens.

Ejemplo:

```text
usuario juan asignar admin
```

se convierte en:

```text
USUARIO
ID(juan)
ASIGNAR
ID(admin)
```

El lexer no verifica la estructura gramatical; únicamente identifica y clasifica los componentes léxicos de la entrada.

---

## 2. Análisis sintáctico

El parser recibe los tokens generados por el lexer y verifica que respeten la gramática definida para SecureAccessLang.

Se implementó un parser:

- Descendente recursivo
- LL(1)
- Sin backtracking
- Con un token de lookahead

La gramática fue diseñada para que las decisiones sintácticas puedan tomarse observando únicamente el token actual.

---

## 3. Construcción del AST

Cuando la entrada es válida, el parser genera un Árbol Sintáctico Abstracto (AST).

Ejemplo:

Entrada:

```text
usuario juan asignar admin
```

AST generado:

```text
programa
  sentencias:
    def_usuario
      nombre: juan
      rol: admin
```

La construcción del AST demuestra que el parser no solo verifica si una cadena pertenece al lenguaje, sino que además obtiene una representación estructurada del programa analizado.

---

## 4. Recuperación de errores en modo pánico

Cuando una entrada contiene múltiples sentencias y una de ellas es inválida, el parser no se detiene: reporta el error con su número de línea, descarta tokens hasta encontrar el inicio de la próxima sentencia válida y continúa el análisis.

Esto permite que una sola llamada a `parse()` procese un programa completo aunque contenga errores intermedios, construyendo un AST parcial con las sentencias que sí fueron reconocidas correctamente.

Ejemplo:

Entrada:

```text
rol admin
usuario asignar admin
login juan password123
```

Resultado:

```text
Error recuperado -> Línea 2: se esperaba 'ID', se obtuvo 'ASIGNAR' ('asignar')

AST parcial:
programa
  sentencias:
    def_rol
      nombre: admin
    login
      usuario: juan
      password: password123
```

La sentencia inválida (línea 2) es reportada y descartada; las sentencias válidas (líneas 1 y 3) se reconocen y se incluyen en el AST.

---

# Requisitos

- Python 3.8 o superior
- PLY (Python Lex-Yacc)

Instalación:

```bash
pip install ply
```

---

# Ejecución

## 1. Ejecutar la batería completa de pruebas

```bash
python test_runner.py
```

El runner:

- Lee los casos desde `casos_prueba.txt`.
- Ejecuta el análisis léxico y sintáctico sobre cada entrada.
- Verifica si el resultado coincide con el esperado (VALIDO, INVALIDO o PARCIAL).
- Genera los árboles sintácticos de los casos válidos y parciales.
- Muestra los errores detectados para los casos inválidos y parciales.
- Presenta un resumen final de resultados.

Ejemplo de salida:

```text
======================================================================
EJECUTANDO CASOS DE PRUEBA DESDE: casos_prueba.txt
======================================================================

[OK] 'rol admin'                              esperado=VALIDO    obtenido=VALIDO
[OK] 'usuario juan asignar admin'             esperado=VALIDO    obtenido=VALIDO
[OK] 'rol admin\nusuario asignar admin\n...'  esperado=PARCIAL   obtenido=PARCIAL

======================================================================
RESUMEN: 25/25 casos correctos
======================================================================
```

Luego se muestran dos secciones adicionales:

```text
======================================================================
ARBOLES GENERADOS (CASOS VALIDOS Y PARCIALES)
======================================================================
```

y

```text
======================================================================
CASOS INVALIDOS Y PARCIALES (errores detectados)
======================================================================
```

donde se presentan los AST generados y los errores sintácticos detectados y recuperados.

También es posible utilizar otro archivo de pruebas:

```bash
python test_runner.py otro_archivo.txt
```

---

## 2. Ejecutar el lexer de forma independiente

```bash
python lexer.py
```

Se ejecutan las cadenas de ejemplo incluidas dentro del archivo y se muestran los tokens producidos por el analizador léxico.

Ejemplo:

```text
Entrada: 'login juan password123'

LexToken(LOGIN,'login',1,0)
LexToken(ID,'juan',1,6)
LexToken(ID,'password123',1,11)
```

Esto permite verificar de manera independiente el funcionamiento del lexer.

---

## 3. Ejecutar el parser de forma independiente

```bash
python parser.py
```

Se ejecutan los casos válidos, inválidos y de recuperación definidos dentro del archivo.

Para los casos válidos se imprime el AST generado.  
Para los casos inválidos se imprime el error sintáctico detectado.  
Para los casos de recuperación se imprimen tanto los errores recuperados como el AST parcial.

Ejemplo (caso válido):

```text
==================================================
CASOS VALIDOS
==================================================

Entrada: 'rol admin'

programa
  sentencias:
    def_rol
      nombre: admin
```

Ejemplo (caso inválido):

```text
==================================================
CASOS INVALIDOS
==================================================

Entrada: 'login juan'

  Detectado correctamente ->
  Se esperaba una contraseña pero se llegó al fin de la entrada
```

Ejemplo (recuperación de errores):

```text
==================================================
CASOS DE RECUPERACION (modo panico, multi-sentencia)
==================================================

Entrada:
rol admin
usuario asignar admin
login juan password123

Errores detectados y recuperados:
  - Línea 2: se esperaba 'ID', se obtuvo 'ASIGNAR' ('asignar')

AST parcial (sentencias válidas reconocidas):
programa
  sentencias:
    def_rol
      nombre: admin
    login
      usuario: juan
      password: password123
```

---

## 4. Utilizar el parser desde código propio

El parser expone una función pública llamada `parse()` que siempre retorna una tupla `(ast, errores)`.

Ejemplo (entrada válida):

```python
from parser import parse

ast, errores = parse("permitir admin acceder dashboard")

print(ast)
# programa
#   sentencias:
#     permiso
#       efecto: permitir
#       rol: admin
#       accion: acceder
#       recurso: dashboard

print(errores)  # []
```

Ejemplo (entrada inválida):

```python
from parser import parse

ast, errores = parse("login juan")

print(errores)
# ['Se esperaba una contraseña pero se llegó al fin de la entrada']

print(ast.attrs['sentencias'])  # [] — ninguna sentencia válida reconocida
```

Ejemplo (entrada con recuperación parcial):

```python
from parser import parse

ast, errores = parse("rol admin\nusuario asignar admin\nlogin juan password123")

print(errores)
# ["Línea 2: se esperaba 'ID', se obtuvo 'ASIGNAR' ('asignar')"]

print(ast)
# programa
#   sentencias:
#     def_rol
#       nombre: admin
#     login
#       usuario: juan
#       password: password123
```

---

# Formato de los casos de prueba

El archivo `casos_prueba.txt` utiliza el formato:

```text
entrada | RESULTADO_ESPERADO
```

donde:

```text
RESULTADO_ESPERADO ∈ { VALIDO, INVALIDO, PARCIAL }
```

| Valor | Significado |
|-------|-------------|
| `VALIDO` | Toda la entrada se reconoce sin errores. |
| `INVALIDO` | La entrada tiene error(es) y ninguna sentencia válida pudo reconocerse. |
| `PARCIAL` | La entrada tiene una o más sentencias con error, pero el parser se recupera y reconoce el resto de las sentencias válidas dentro de esa misma entrada. |

Ejemplos:

```text
rol admin | VALIDO

usuario asignar admin | INVALIDO

login juan password123 | VALIDO

rol admin\nusuario asignar admin\nlogin juan password123 | PARCIAL
```

Las líneas vacías y las que comienzan con `#` se ignoran automáticamente.

Para representar programas de múltiples líneas se utiliza la secuencia literal `\n`:

```text
rol admin\nusuario juan asignar admin\nlogin juan password123 | VALIDO
```

Durante la ejecución del runner dicha secuencia se convierte automáticamente en saltos de línea reales.

Agregar nuevos casos de prueba solo requiere añadir nuevas líneas a este archivo, sin necesidad de modificar el código fuente.

> **Nota importante sobre PARCIAL:** la recuperación de errores ocurre *dentro* de una misma llamada a `parse()`, no como efecto de llamar al parser línea por línea. Los casos PARCIAL deben integrar varias sentencias en una sola entrada para ejercitar la recuperación real.

---

# Clasificación de resultados

El test runner clasifica cada resultado según la tupla `(ast, errores)` que retorna `parse()`:

| Clasificación | Condición |
|---------------|-----------|
| `VALIDO` | `errores` está vacío. |
| `PARCIAL` | `errores` no está vacío **y** `ast` contiene al menos una sentencia válida. |
| `INVALIDO` | `errores` no está vacío **y** `ast` no contiene ninguna sentencia válida. |

---

# Manejo de errores sintácticos

El parser produce mensajes descriptivos cuando encuentra una violación de la gramática.

Ejemplos:

Entrada:

```text
usuario asignar admin
```

Salida:

```text
Línea 1: se esperaba 'ID', se obtuvo 'ASIGNAR' ('asignar')
```

---

Entrada:

```text
mfa juan volar
```

Salida:

```text
Línea 1: se esperaba 'activar' o 'desactivar', se obtuvo 'volar'
```

---

Entrada:

```text
login juan
```

Salida:

```text
Se esperaba una contraseña pero se llegó al fin de la entrada
```

Estos mensajes permiten identificar con precisión la causa del error y el punto de la gramática donde se produjo.

---

# Gramática

La gramática consta de veintidós producciones. El terminal `ID` es reconocido directamente por el lexer mediante la expresión regular `[A-Za-z0-9_@#$!]+`; la gramática formal lo trata como un terminal atómico, delegando su estructura interna al análisis léxico.

```text
<programa>    ::= <lista_sentencias>
<lista_sent.> ::= <sentencia>
                | <sentencia> <lista_sent.>
<sentencia>   ::= <def_rol> | <def_usuario>
                | <login>   | <logout>
                | <mfa>     | <permiso>
<def_rol>     ::= "rol" ID
<def_usuario> ::= "usuario" ID "asignar" ID
<login>       ::= "login" ID <password>
<logout>      ::= "logout" ID
<mfa>         ::= "mfa" ID <estado_mfa>
<estado_mfa>  ::= "activar" | "desactivar"
<permiso>     ::= <efecto> ID <accion> <recurso>
<efecto>      ::= "permitir" | "denegar"
<accion>      ::= ID
<recurso>     ::= ID
<password>    ::= ID
```

La demostración formal de que la gramática pertenece a la clase LL(1) —incluyendo el cálculo de los conjuntos FIRST y FOLLOW y la verificación de ausencia de conflictos— se encuentra documentada en el informe técnico entregado junto al proyecto.

El parser implementa un analizador descendente recursivo LL(1), tomando decisiones mediante un único token de lookahead y sin necesidad de retroceso (backtracking).

---

# Tecnologías utilizadas

- Python 3
- PLY (Python Lex-Yacc)
- Analizador Descendente Recursivo LL(1)
- AST (Abstract Syntax Tree)
- Recuperación de errores en modo pánico

---

# Autoría

Proyecto desarrollado como Trabajo Integrador para la asignatura Teoría de la Computación.

Universidad Nacional del Nordeste (UNNE)  
Facultad de Ciencias Exactas y Naturales y Agrimensura (FaCENA)  
Licenciatura en Sistemas de Información