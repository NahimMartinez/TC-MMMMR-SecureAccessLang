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
- **parser.py**: analizador sintáctico descendente recursivo LL(1) y construcción del AST.
- **casos_prueba.txt**: conjunto de casos válidos e inválidos.
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
- Verifica si el resultado coincide con el esperado.
- Genera los árboles sintácticos de los casos válidos.
- Muestra los errores detectados para los casos inválidos.
- Presenta un resumen final de resultados.

Ejemplo de salida:

```text
======================================================================
EJECUTANDO CASOS DE PRUEBA DESDE: casos_prueba.txt
======================================================================

[OK] 'rol admin' esperado=VALIDO obtenido=VALIDO
[OK] 'usuario juan asignar admin' esperado=VALIDO obtenido=VALIDO

======================================================================
RESUMEN: 19/19 casos correctos
======================================================================
```

Luego se muestran dos secciones adicionales:

```text
======================================================================
ARBOLES GENERADOS (CASOS VALIDOS)
======================================================================
```

y

```text
======================================================================
CASOS INVALIDOS
======================================================================
```

donde se presentan los AST generados y los errores sintácticos detectados correctamente.

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

Se ejecutan los casos válidos e inválidos definidos dentro del archivo.

Para los casos válidos se imprime el AST generado.

Para los casos inválidos se imprime el error sintáctico detectado.

Ejemplo:

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

y

```text
==================================================
CASOS INVALIDOS
==================================================

Entrada: 'login juan'

  Detectado correctamente ->
  Se esperaba una contraseña pero se llegó al fin de la entrada
```

---

## 4. Utilizar el parser desde código propio

El parser expone una función pública llamada `parse()`.

Ejemplo:

```python
from parser import parse

ast = parse("permitir admin acceder dashboard")

print(ast)
```

Salida:

```text
programa
  sentencias:
    permiso
      efecto: permitir
      rol: admin
      accion: acceder
      recurso: dashboard
```

Si la entrada es inválida:

```python
from parser import parse

parse("login juan")
```

se lanza una excepción:

```text
SyntaxError:
Se esperaba una contraseña pero se llegó al fin de la entrada
```

---

# Formato de los casos de prueba

El archivo `casos_prueba.txt` utiliza el formato:

```text
entrada | RESULTADO_ESPERADO
```

donde:

```text
RESULTADO_ESPERADO ∈ { VALIDO, INVALIDO }
```

Ejemplos:

```text
rol admin | VALIDO

usuario asignar admin | INVALIDO

login juan password123 | VALIDO
```

Las líneas vacías y las que comienzan con `#` se ignoran automáticamente.

Para representar programas de múltiples líneas se utiliza la secuencia literal `\n`:

```text
rol admin\nusuario juan asignar admin\nlogin juan password123 | VALIDO
```

Durante la ejecución del runner dicha secuencia se convierte automáticamente en saltos de línea reales.

Agregar nuevos casos de prueba solo requiere añadir nuevas líneas a este archivo, sin necesidad de modificar el código fuente.

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

La definición formal de la gramática, el cálculo de los conjuntos FIRST y FOLLOW y la demostración de que la gramática pertenece a la clase LL(1) se encuentran documentados en el informe técnico entregado junto al proyecto.

El parser implementa un analizador descendente recursivo LL(1), tomando decisiones mediante un único token de lookahead y sin necesidad de retroceso (backtracking).

---

# Tecnologías utilizadas

- Python 3
- PLY (Python Lex-Yacc)
- Analizador Descendente Recursivo LL(1)
- AST (Abstract Syntax Tree)

---

# Autoría

Proyecto desarrollado como Trabajo Integrador para la asignatura Teoría de la Computación.

Universidad Nacional del Nordeste (UNNE)  
Facultad de Ciencias Exactas y Naturales y Agrimensura (FaCENA)  
Licenciatura en Sistemas de Información