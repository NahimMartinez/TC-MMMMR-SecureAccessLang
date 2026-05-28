import ply.lex as lex

# =============================================================================
# ANALIZADOR LÉXICO — SecureAccessLang
# =============================================================================
# El analizador léxico (lexer) es la primera etapa del análisis. Su trabajo es
# leer el texto de entrada carácter por carácter y agruparlos en unidades con
# significado llamadas TOKENS. Por ejemplo, la cadena "usuario juan asignar admin"
# se convierte en: [USUARIO, ID("juan"), ASIGNAR, ID("admin")].
#
# El lexer NO verifica si la estructura es correcta, solo identifica piezas.
# Eso es tarea del parser (segunda etapa).
# =============================================================================


# -----------------------------------------------------------------------------
# 1. PALABRAS RESERVADAS
# -----------------------------------------------------------------------------
# Son palabras que tienen un significado fijo en el lenguaje y no pueden usarse
# como identificadores (nombres de usuario, rol, etc.).
# El diccionario mapea: texto_en_el_código → nombre_interno_del_token
# Ejemplo: si el lexer encuentra "login", lo clasifica como token LOGIN.
reserved = {
    'rol':          'ROL',
    'usuario':      'USUARIO',
    'asignar':      'ASIGNAR',
    'login':        'LOGIN',
    'logout':       'LOGOUT',
    'mfa':          'MFA',
    'activar':      'ACTIVAR',
    'desactivar':   'DESACTIVAR',
    'permitir':     'PERMITIR',
    'denegar':      'DENEGAR',
    'leer':         'LEER',
    'escribir':     'ESCRIBIR',
    'eliminar':     'ELIMINAR',
    'acceder':      'ACCEDER',
    'dashboard':    'DASHBOARD',
    'usuarios':     'USUARIOS',
    'reportes':     'REPORTES',
    'configuracion':'CONFIGURACION',
}

# -----------------------------------------------------------------------------
# 2. LISTA DE TODOS LOS TOKENS
# -----------------------------------------------------------------------------
# PLY requiere una lista llamada exactamente "tokens" con todos los tipos posibles.
# 'ID' representa cualquier identificador que NO sea palabra reservada
# (ej: "juan", "admin", "password123").
# Los valores del diccionario reserved son el resto de los tokens posibles.
tokens = ['ID'] + list(reserved.values())

# -----------------------------------------------------------------------------
# 3. CARACTERES IGNORADOS
# -----------------------------------------------------------------------------
# t_ignore le dice a PLY qué caracteres saltar sin generar ningún token.
# Los espacios y tabulaciones son separadores, no tienen significado propio.
t_ignore = ' \t'


# -----------------------------------------------------------------------------
# 4. REGLA PARA IDENTIFICADORES
# -----------------------------------------------------------------------------
# PLY lee la expresión regular directamente del docstring de la función (r'...').
# Esta regex captura: una letra minúscula seguida de cero o más letras/dígitos.
# Ejemplos válidos: "juan", "admin", "password123", "a"
# Ejemplos inválidos: "Juan" (mayúscula), "123abc" (empieza con número)
#
# Después de capturar la palabra, se verifica si está en el diccionario de
# palabras reservadas. Si está → se le asigna el tipo reservado (ej: USUARIO).
# Si no está → queda como ID genérico.
def t_ID(t):
    r'[a-z][a-z0-9]*'
    t.type = reserved.get(t.value, 'ID')
    return t


# -----------------------------------------------------------------------------
# 5. REGLA PARA SALTOS DE LÍNEA
# -----------------------------------------------------------------------------
# Los saltos de línea no generan tokens (no se retorna nada), pero sí se usa
# el contador t.lexer.lineno para saber en qué línea estamos. Esto es crucial
# para que los mensajes de error puedan indicar "error en línea X".
# El += len(t.value) maneja múltiples saltos consecutivos (\n\n\n → suma 3).
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# -----------------------------------------------------------------------------
# 6. MANEJO DE ERRORES LÉXICOS
# -----------------------------------------------------------------------------
# Si el lexer encuentra un carácter que ninguna regla puede reconocer
# (ej: "@", "!", "Ñ"), cae en esta función.
# - Imprime un mensaje indicando el carácter y la línea donde ocurrió.
# - t.lexer.skip(1) salta ese carácter y continúa analizando el resto,
#   así un solo error no detiene todo el análisis.
def t_error(t):
    print(f"Error léxico: Carácter no válido '{t.value[0]}' en la línea {t.lexer.lineno}")
    t.lexer.skip(1)


# -----------------------------------------------------------------------------
# 7. CONSTRUCCIÓN DEL LEXER
# -----------------------------------------------------------------------------
# lex.lex() lee todas las funciones y variables t_ definidas arriba,
# compila las expresiones regulares y construye la máquina del analizador.
# El objeto resultante es el lexer listo para usar.
lexer = lex.lex()


# -----------------------------------------------------------------------------
# ZONA DE PRUEBAS
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    data = "usuario juan asignar admin \n login juan password123"
    lexer.input(data)
    for tok in lexer:
        print(tok)
