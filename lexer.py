import ply.lex as lex

"""
Definición de palabras reservadas, a la izquierda son las palabras exactas que el usuario debe escribir en su código y
a la derecha las etiquetas que el analizador utiliza para identificarlas internamente.
"""
reserved = {
    'rol': 'ROL',
    'usuario': 'USUARIO',
    'asignar': 'ASIGNAR',
    'login': 'LOGIN',
    'logout': 'LOGOUT',
    'mfa': 'MFA',
    'activar': 'ACTIVAR',
    'desactivar': 'DESACTIVAR',
    'permitir': 'PERMITIR',
    'denegar': 'DENEGAR',
    'leer': 'LEER',
    'escribir': 'ESCRIBIR',
    'eliminar': 'ELIMINAR',
    'acceder': 'ACCEDER',
    'dashboard': 'DASHBOARD',
    'usuarios': 'USUARIOS',
    'reportes': 'REPORTES',
    'configuracion': 'CONFIGURACION'
}

"""
Lista de tokens. Se toman los valores del diccionario de palabras reservadas y se le suma la etiqueta ID que representa
cualquier palabra que no sea reserva, por ejemplo: "juan"
"""
tokens = ['ID'] + list(reserved.values())

# Reglas de expresiones regulares
# Ignorar espacios y tabulaciones
t_ignore = ' \t'


"""
Regla para identificadores (letras minúsculas y dígitos según su BNF)
PLY lee esta expresión regular directamente de la documentación de la función para saber qué formato debe tener el token
(una letra minúscula seguida de letras o números)
"""
def t_ID(t):
    r'[a-z][a-z0-9]*'
    # Verificamos si el identificador es en realidad una palabra reservada, si lo es se le asigna una etiqueta, si no
    # le asigna por defecto la etiqueta genérica ID
    t.type = reserved.get(t.value, 'ID')
    return t

"""
Si el analizador se cruza con un símbolo que no definimos en ninguna regla (por ejemplo, un @ o un !), cae acá. 
Imprime un mensaje indicando el problema y la línea, y luego usa t.lexer.skip(1) para saltar ese carácter 
problemático y seguir analizando el resto del texto sin que se caiga el programa.
"""
def t_error(t):
    print(f"Error léxico: Carácter no válido '{t.value[0]}' en la línea {t.lexer.lineno}")
    t.lexer.skip(1)

"""
Busca los saltos de línea (\n), suma la cantidad de saltos de línea 
encontrados al contador interno (t.lexer.lineno += len(t.value)). Esto es fundamental para que, si hay un error, 
el sistema te pueda decir exactamente en qué línea del archivo ocurrió.
"""
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

"""
Compila todas las variables tokens y las reglas t_ que definimos, 
y construye la "máquina" del analizador léxico.
"""
lexer = lex.lex()

"""
Prueba. Simulamos datos con la variable data, le inyectamos el texto a la máquina con el input, luego
itera sobre el analizador. En cada vuelta del bucle, el lexer procesa la siguiente porción de texto, 
aplica las reglas devuelve el token procesado hasta llegar al final.
"""
if __name__ == '__main__':
    data = "usuario juan asignar admin \n login juan password123"
    lexer.input(data)
    for tok in lexer:
        print(tok)