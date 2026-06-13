from lexer import lexer

# =============================================================================
# ANALIZADOR SINTÁCTICO (PARSER) — SecureAccessLang
# =============================================================================
# El parser es la segunda etapa del análisis. Recibe la lista de tokens que
# produjo el lexer y verifica que estén en el orden correcto según la gramática.
#
# Se implementa un ANALIZADOR DESCENDENTE RECURSIVO LL(1): lee la entrada de
# izquierda a derecha y decide qué producción aplicar mirando un solo token de
# lookahead (el token actual), sin retroceder nunca.
#
# LL(1) significa:
#   - L: Left-to-right (lectura de izquierda a derecha)
#   - L: Leftmost derivation (derivación por la izquierda)
#   - (1): un solo token de lookahead para decidir
#
# Esto es posible porque los conjuntos FIRST de cada alternativa son disjuntos,
# garantizando una única decisión posible en cada paso (ver justificación
# FIRST/FOLLOW en el documento adjunto).
#
# Si la entrada es válida, construye un AST (Árbol Sintáctico Abstracto)
# que representa la estructura jerárquica del programa.
# Si la entrada es inválida, lanza un SyntaxError con el número de línea.
#
# Flujo completo:
#   Texto -> [Lexer] -> lista de tokens -> [Parser LL(1)] -> AST
# =============================================================================


# =============================================================================
# CLASE NODE — Nodo del Árbol Sintáctico Abstracto (AST)
# =============================================================================
# Cada nodo representa un elemento de la gramática (una sentencia, un permiso,
# etc.). El árbol resultante muestra la estructura jerárquica del programa.
#
# Ejemplo para "usuario juan asignar admin":
#   Node('def_usuario', nombre='juan', rol='admin')
#
# Se imprime con sangría para visualizarlo como árbol:
#   def_usuario
#     nombre: juan
#     rol: admin
class Node:
    def __init__(self, tipo, **attrs):
        # tipo: nombre de la producción (ej: 'def_usuario', 'permiso')
        # attrs: los datos del nodo como pares clave=valor
        self.tipo = tipo
        self.attrs = attrs

    def __repr__(self):
        return self._fmt(0)

    def _fmt(self, indent):
        # Construye la representación visual con sangría para ver la jerarquía.
        # Cada nivel de profundidad agrega 2 espacios de sangría.
        pad = '  ' * indent
        lines = [f"{pad}{self.tipo}"]
        for key, val in self.attrs.items():
            if isinstance(val, Node):
                lines.append(f"{pad}  {key}:")
                lines.append(val._fmt(indent + 2))
            elif isinstance(val, list):
                lines.append(f"{pad}  {key}:")
                for item in val:
                    lines.append(item._fmt(indent + 2) if isinstance(item, Node) else f"{'  ' * (indent+2)}{item}")
            else:
                lines.append(f"{pad}  {key}: {val}")
        return '\n'.join(lines)


# =============================================================================
# CLASE PARSER — Analizador Sintáctico Descendente Recursivo LL(1)
# =============================================================================
class Parser:
    def __init__(self, tokens):
        # tokens: lista completa de tokens producida por el lexer
        # pos: índice del token que estamos analizando actualmente
        self.tokens = tokens
        self.pos = 0

    def current(self):
        """Devuelve el token actual sin consumirlo (lookahead). Retorna None al final."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_type):
        """
        Verifica que el token actual sea del tipo esperado y avanza al siguiente.
        Es el mecanismo central del parser LL(1): cada llamada a consume() acepta
        un terminal de la gramática.

        Si el token no coincide con lo esperado, lanza SyntaxError indicando
        en qué línea ocurrió el error y qué se esperaba vs qué llegó.
        """
        tok = self.current()
        if tok is None:
            raise SyntaxError(f"Se esperaba '{expected_type}' pero se llegó al fin de la entrada")
        if tok.type != expected_type:
            raise SyntaxError(
                f"Línea {tok.lineno}: se esperaba '{expected_type}', "
                f"se obtuvo '{tok.type}' ('{tok.value}')"
            )
        self.pos += 1
        return tok

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <programa> -> <lista_sentencias>
    # -------------------------------------------------------------------------
    # Punto de entrada del parser. Analiza el programa completo.
    # Al final verifica que no haya tokens sobrantes (si los hay, la entrada
    # tiene algo extra que la gramática no contempla).
    #
    # FIRST(<programa>) = FIRST(<lista_sentencias>)
    #                   = { rol, usuario, login, logout, mfa, permitir, denegar }
    def parse_programa(self):
        sentencias = self.parse_lista_sentencias()
        if self.current() is not None:
            tok = self.current()
            raise SyntaxError(f"Línea {tok.lineno}: token inesperado '{tok.value}'")
        return Node('programa', sentencias=sentencias)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <lista_sentencias> -> <sentencia> | <sentencia> <lista_sentencias>
    # -------------------------------------------------------------------------
    # Analiza una o más sentencias seguidas. El bucle while continúa mientras
    # haya tokens de inicio de sentencia disponibles.
    #
    # FIRST(<lista_sentencias>) = { rol, usuario, login, logout, mfa, permitir, denegar }
    # FOLLOW(<lista_sentencias>) = { $ }
    def parse_lista_sentencias(self):
        sentencias = []
        inicio_sentencia = {'ROL', 'USUARIO', 'LOGIN', 'LOGOUT', 'MFA', 'PERMITIR', 'DENEGAR'}
        while self.current() is not None and self.current().type in inicio_sentencia:
            sentencias.append(self.parse_sentencia())
        return sentencias

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <sentencia> -> <def_rol> | <def_usuario> | <login> |
    #                            <logout> | <mfa> | <permiso>
    # -------------------------------------------------------------------------
    # Mira el token actual (lookahead) para decidir qué producción aplicar.
    # Cada alternativa comienza con un terminal distinto: sin conflicto LL(1).
    #
    # FIRST(<sentencia>) = { rol, usuario, login, logout, mfa, permitir, denegar }
    def parse_sentencia(self):
        tok = self.current()
        if tok is None:
            raise SyntaxError("Se esperaba una sentencia pero se llegó al fin de la entrada")

        if tok.type == 'ROL':
            return self.parse_def_rol()
        elif tok.type == 'USUARIO':
            return self.parse_def_usuario()
        elif tok.type == 'LOGIN':
            return self.parse_login()
        elif tok.type == 'LOGOUT':
            return self.parse_logout()
        elif tok.type == 'MFA':
            return self.parse_mfa()
        elif tok.type in ('PERMITIR', 'DENEGAR'):
            return self.parse_permiso()
        else:
            raise SyntaxError(
                f"Línea {tok.lineno}: inicio de sentencia inválido '{tok.value}'"
            )

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <def_rol> -> "rol" <identificador>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "rol admin"
    # Consume el terminal "rol" y luego un ID (el nombre del rol).
    #
    # FIRST(<def_rol>) = { rol }
    def parse_def_rol(self):
        self.consume('ROL')
        nombre = self.consume('ID')
        return Node('def_rol', nombre=nombre.value)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <def_usuario> -> "usuario" <identificador> "asignar" <identificador>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "usuario juan asignar admin"
    # El primer ID es el nombre del usuario, el segundo es el rol asignado.
    #
    # FIRST(<def_usuario>) = { usuario }
    def parse_def_usuario(self):
        self.consume('USUARIO')
        nombre = self.consume('ID')
        self.consume('ASIGNAR')
        rol = self.consume('ID')
        return Node('def_usuario', nombre=nombre.value, rol=rol.value)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <login> -> "login" <identificador> <password>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "login juan password123"
    # La contraseña se consume con parse_password() para reflejar que
    # <password> es un no-terminal distinto en la gramática.
    #
    # FIRST(<login>) = { login }
    def parse_login(self):
        self.consume('LOGIN')
        usuario = self.consume('ID')
        password = self.parse_password()
        return Node('login', usuario=usuario.value, password=password)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <logout> -> "logout" <identificador>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "logout juan"
    #
    # FIRST(<logout>) = { logout }
    def parse_logout(self):
        self.consume('LOGOUT')
        usuario = self.consume('ID')
        return Node('logout', usuario=usuario.value)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <mfa> -> "mfa" <identificador> <estado_mfa>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "mfa juan activar"
    #
    # FIRST(<mfa>) = { mfa }
    def parse_mfa(self):
        self.consume('MFA')
        usuario = self.consume('ID')
        estado = self.parse_estado_mfa()
        return Node('mfa', usuario=usuario.value, estado=estado)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <estado_mfa> -> "activar" | "desactivar"
    # -------------------------------------------------------------------------
    # FIRST(<estado_mfa>) = { activar, desactivar } -> sin conflicto LL(1).
    # FOLLOW(<estado_mfa>) = FOLLOW(<mfa>) = { rol, usuario, login, logout,
    #                                          mfa, permitir, denegar, $ }
    def parse_estado_mfa(self):
        tok = self.current()
        if tok and tok.type == 'ACTIVAR':
            self.consume('ACTIVAR')
            return 'activar'
        elif tok and tok.type == 'DESACTIVAR':
            self.consume('DESACTIVAR')
            return 'desactivar'
        else:
            val = tok.value if tok else 'fin de entrada'
            linea = tok.lineno if tok else '?'
            raise SyntaxError(
                f"Línea {linea}: se esperaba 'activar' o 'desactivar', se obtuvo '{val}'"
            )

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <permiso> -> <efecto> <identificador> <accion> <recurso>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "permitir admin acceder dashboard"
    #
    # FIRST(<permiso>) = FIRST(<efecto>) = { permitir, denegar }
    def parse_permiso(self):
        efecto = self.parse_efecto()
        rol = self.consume('ID')
        accion = self.parse_accion()
        recurso = self.parse_recurso()
        return Node('permiso', efecto=efecto, rol=rol.value, accion=accion, recurso=recurso)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <efecto> -> "permitir" | "denegar"
    # -------------------------------------------------------------------------
    # FIRST(<efecto>) = { permitir, denegar } -> sin conflicto LL(1).
    # FOLLOW(<efecto>) = FIRST(<identificador>) = { ID }
    def parse_efecto(self):
        tok = self.current()
        if tok and tok.type == 'PERMITIR':
            self.consume('PERMITIR')
            return 'permitir'
        elif tok and tok.type == 'DENEGAR':
            self.consume('DENEGAR')
            return 'denegar'
        else:
            val = tok.value if tok else 'fin de entrada'
            linea = tok.lineno if tok else '?'
            raise SyntaxError(
                f"Línea {linea}: se esperaba 'permitir' o 'denegar', se obtuvo '{val}'"
            )

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <accion> -> <identificador>
    # -------------------------------------------------------------------------
    # CORRECCIÓN: antes validaba el valor contra un conjunto fijo {'leer', 'escribir'...}
    # lo que limitaba la extensibilidad (observación del docente).
    # Ahora acepta cualquier ID, igual que <identificador>.
    # La restricción de qué acciones son válidas es responsabilidad semántica,
    # no gramatical: la gramática solo verifica estructura.
    #
    # FIRST(<accion>) = FIRST(<identificador>) = { ID }
    # FOLLOW(<accion>) = FIRST(<recurso>) = { ID }
    def parse_accion(self):
        tok = self.current()
        if tok is None:
            raise SyntaxError("Se esperaba una acción pero se llegó al fin de la entrada")
        if tok.type != 'ID':
            raise SyntaxError(
                f"Línea {tok.lineno}: se esperaba una acción (identificador), "
                f"se obtuvo '{tok.type}' ('{tok.value}')"
            )
        self.pos += 1
        return tok.value

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <recurso> -> <identificador>
    # -------------------------------------------------------------------------
    # CORRECCIÓN: misma situación que parse_accion(). Antes validaba contra
    # {'dashboard', 'usuarios'...}, limitando la extensibilidad.
    # Ahora acepta cualquier ID.
    #
    # FIRST(<recurso>) = FIRST(<identificador>) = { ID }
    # FOLLOW(<recurso>) = FOLLOW(<permiso>) = { rol, usuario, login, logout,
    #                                           mfa, permitir, denegar, $ }
    def parse_recurso(self):
        tok = self.current()
        if tok is None:
            raise SyntaxError("Se esperaba un recurso pero se llegó al fin de la entrada")
        if tok.type != 'ID':
            raise SyntaxError(
                f"Línea {tok.lineno}: se esperaba un recurso (identificador), "
                f"se obtuvo '{tok.type}' ('{tok.value}')"
            )
        self.pos += 1
        return tok.value

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <password> -> <identificador>
    # -------------------------------------------------------------------------
    # Acepta cualquier token ID como contraseña. El lexer amplió el regex
    # para incluir caracteres especiales (@, #, $, !) válidos en contraseñas.
    #
    # FIRST(<password>) = FIRST(<identificador>) = { ID }
    # FOLLOW(<password>) = FOLLOW(<login>) = { rol, usuario, login, logout,
    #                                          mfa, permitir, denegar, $ }
    def parse_password(self):
        tok = self.current()
        if tok is None:
            raise SyntaxError("Se esperaba una contraseña pero se llegó al fin de la entrada")
        if tok.type != 'ID':
            raise SyntaxError(
                f"Línea {tok.lineno}: se esperaba una contraseña, "
                f"se obtuvo '{tok.type}' ('{tok.value}')"
            )
        self.pos += 1
        return tok.value


# =============================================================================
# FUNCIÓN PRINCIPAL — parse()
# =============================================================================
# Función de entrada pública: recibe un texto, lo tokeniza y lo parsea.
#
# Importante: lexer.lineno debe resetearse a 1 antes de cada llamada porque
# PLY no lo hace automáticamente. Sin este reset, si se parsean múltiples
# textos seguidos, el número de línea en los errores sería incorrecto.
def parse(texto):
    lexer.lineno = 1
    lexer.input(texto)
    tok_list = list(lexer)
    return Parser(tok_list).parse_programa()


# =============================================================================
# CASOS DE PRUEBA
# =============================================================================
if __name__ == '__main__':
    casos_validos = [
        "rol admin",
        "usuario juan asignar admin",
        "login juan password123",
        "logout juan",
        "mfa juan activar",
        "mfa root desactivar",
        "permitir admin acceder dashboard",
        "denegar invitado eliminar usuarios",
        "permitir editor escribir reportes",
        "login juan P@ss_1",
        "login juan Adm!n#2026",
        "permitir dev ejecutar pipeline",
        "permitir editor escribir archivos",
        # Programa con múltiples sentencias (saltos de línea como separadores)
        (
            "rol admin\n"
            "usuario juan asignar admin\n"
            "login juan password123\n"
            "permitir admin acceder dashboard"
        ),
    ]

    # Con <accion> y <recurso> como <identificador> extensible, ya no se
    # rechazan valores semánticamente desconocidos a nivel gramatical.
    # Los errores detectables son los estructurales (tokens faltantes o
    # palabras reservadas en lugar de identificadores).
    casos_invalidos = [
        ("usuario asignar admin",   "falta nombre de usuario"),
        ("mfa juan volar",          "estado_mfa invalido: 'volar' no es activar/desactivar"),
        ("login juan",              "falta password"),
        ("permitir admin",          "falta accion y recurso"),
        ("denegar",                 "falta identificador, accion y recurso"),
    ]

    print("=" * 50)
    print("CASOS VALIDOS")
    print("=" * 50)
    for caso in casos_validos:
        print(f"\nEntrada: {repr(caso)}")
        try:
            ast = parse(caso)
            print(ast)
        except SyntaxError as e:
            print(f"  ERROR inesperado -> {e}")

    print("\n" + "=" * 50)
    print("CASOS INVALIDOS")
    print("=" * 50)
    for caso, descripcion in casos_invalidos:
        print(f"\nEntrada: {repr(caso)}  ({descripcion})")
        try:
            ast = parse(caso)
            print(f"  ERROR: deberia fallar pero produjo -> {ast}")
        except SyntaxError as e:
            print(f"  Detectado correctamente -> {e}")
