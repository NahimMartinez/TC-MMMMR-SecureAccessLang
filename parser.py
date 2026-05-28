from lexer import lexer

# =============================================================================
# ANALIZADOR SINTÁCTICO (PARSER) — SecureAccessLang
# =============================================================================
# El parser es la segunda etapa del análisis. Recibe la lista de tokens que
# produjo el lexer y verifica que estén en el orden correcto según la gramática.
#
# Se usa la técnica de PARSER DESCENDENTE RECURSIVO: cada producción de la
# gramática BNF se convierte directamente en una función de Python.
#
# Si la entrada es válida, construye un AST (Árbol Sintáctico Abstracto)
# que representa la estructura jerárquica del programa.
# Si la entrada es inválida, lanza un SyntaxError con el número de línea.
#
# Flujo completo:
#   Texto → [Lexer] → lista de tokens → [Parser] → AST
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
# CLASE PARSER — Analizador Sintáctico Descendente Recursivo
# =============================================================================
class Parser:
    def __init__(self, tokens):
        # tokens: lista completa de tokens producida por el lexer
        # pos: índice del token que estamos analizando actualmente
        self.tokens = tokens
        self.pos = 0

    def current(self):
        """Devuelve el token actual sin consumirlo. Retorna None si llegamos al final."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_type):
        """
        Verifica que el token actual sea del tipo esperado y avanza al siguiente.
        Es el mecanismo central del parser: cada llamada a consume() "acepta"
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
    # PRODUCCIÓN: <programa> → <lista_sentencias>
    # -------------------------------------------------------------------------
    # Punto de entrada del parser. Analiza el programa completo.
    # Al final verifica que no haya tokens sobrantes (si los hay, la entrada
    # tiene algo extra que la gramática no contempla).
    def parse_programa(self):
        sentencias = self.parse_lista_sentencias()
        if self.current() is not None:
            tok = self.current()
            raise SyntaxError(f"Línea {tok.lineno}: token inesperado '{tok.value}'")
        return Node('programa', sentencias=sentencias)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <lista_sentencias> → <sentencia> | <sentencia> <lista_sentencias>
    # -------------------------------------------------------------------------
    # Analiza una o más sentencias seguidas. El bucle while continúa mientras
    # haya tokens disponibles, acumulando cada sentencia en la lista.
    def parse_lista_sentencias(self):
        sentencias = []
        while self.current() is not None:
            sentencias.append(self.parse_sentencia())
        return sentencias

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <sentencia> → <def_rol> | <def_usuario> | <login> |
    #                           <logout> | <mfa> | <permiso>
    # -------------------------------------------------------------------------
    # Mira el token actual (sin consumirlo) para decidir qué tipo de sentencia
    # viene. Esto es posible porque cada sentencia empieza con una palabra
    # reservada diferente — la gramática es LL(1): con mirar 1 token alcanza
    # para saber qué producción aplicar.
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
    # PRODUCCIÓN: <def_rol> → "rol" <identificador>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "rol admin"
    # Consume la palabra "rol" y luego espera un identificador (el nombre del rol).
    def parse_def_rol(self):
        self.consume('ROL')
        nombre = self.consume('ID')
        return Node('def_rol', nombre=nombre.value)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <def_usuario> → "usuario" <identificador> "asignar" <identificador>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "usuario juan asignar admin"
    # El primer ID es el nombre del usuario, el segundo es el rol que se le asigna.
    def parse_def_usuario(self):
        self.consume('USUARIO')
        nombre = self.consume('ID')
        self.consume('ASIGNAR')
        rol = self.consume('ID')
        return Node('def_usuario', nombre=nombre.value, rol=rol.value)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <login> → "login" <identificador> <password>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "login juan password123"
    # <password> → <identificador>, por eso se consume con 'ID' también.
    def parse_login(self):
        self.consume('LOGIN')
        usuario = self.consume('ID')
        password = self.consume('ID')
        return Node('login', usuario=usuario.value, password=password.value)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <logout> → "logout" <identificador>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "logout juan"
    def parse_logout(self):
        self.consume('LOGOUT')
        usuario = self.consume('ID')
        return Node('logout', usuario=usuario.value)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <mfa> → "mfa" <identificador> <estado_mfa>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "mfa juan activar"
    # El estado_mfa es un no-terminal con sus propias opciones, se delega a
    # parse_estado_mfa().
    def parse_mfa(self):
        self.consume('MFA')
        usuario = self.consume('ID')
        estado = self.parse_estado_mfa()
        return Node('mfa', usuario=usuario.value, estado=estado)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <estado_mfa> → "activar" | "desactivar"
    # -------------------------------------------------------------------------
    # Solo acepta exactamente esas dos palabras. Cualquier otra cosa es error.
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
    # PRODUCCIÓN: <permiso> → <efecto> <identificador> <accion> <recurso>
    # -------------------------------------------------------------------------
    # Ejemplo válido: "permitir admin acceder dashboard"
    # Cada parte es un no-terminal distinto, se delega a sus funciones.
    def parse_permiso(self):
        efecto = self.parse_efecto()
        rol = self.consume('ID')
        accion = self.parse_accion()
        recurso = self.parse_recurso()
        return Node('permiso', efecto=efecto, rol=rol.value, accion=accion, recurso=recurso)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <efecto> → "permitir" | "denegar"
    # -------------------------------------------------------------------------
    # Indica si el permiso concede o niega el acceso.
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
    # PRODUCCIÓN: <accion> → "leer" | "escribir" | "eliminar" | "acceder"
    # -------------------------------------------------------------------------
    # Define qué operación se permite o deniega sobre el recurso.
    # Se usa un diccionario para mapear el tipo del token a su valor en texto.
    def parse_accion(self):
        tok = self.current()
        opciones = {'LEER': 'leer', 'ESCRIBIR': 'escribir', 'ELIMINAR': 'eliminar', 'ACCEDER': 'acceder'}
        if tok and tok.type in opciones:
            self.pos += 1
            return opciones[tok.type]
        val = tok.value if tok else 'fin de entrada'
        linea = tok.lineno if tok else '?'
        raise SyntaxError(
            f"Línea {linea}: se esperaba una acción (leer/escribir/eliminar/acceder), se obtuvo '{val}'"
        )

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <recurso> → "dashboard" | "usuarios" | "reportes" | "configuracion"
    # -------------------------------------------------------------------------
    # Los recursos son los elementos del sistema sobre los que se aplican permisos.
    def parse_recurso(self):
        tok = self.current()
        opciones = {
            'DASHBOARD':     'dashboard',
            'USUARIOS':      'usuarios',
            'REPORTES':      'reportes',
            'CONFIGURACION': 'configuracion',
        }
        if tok and tok.type in opciones:
            self.pos += 1
            return opciones[tok.type]
        val = tok.value if tok else 'fin de entrada'
        linea = tok.lineno if tok else '?'
        raise SyntaxError(
            f"Línea {linea}: se esperaba un recurso (dashboard/usuarios/reportes/configuracion), se obtuvo '{val}'"
        )


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
        # Programa con múltiples sentencias (saltos de línea como separadores)
        (
            "rol admin\n"
            "usuario juan asignar admin\n"
            "login juan password123\n"
            "permitir admin acceder dashboard"
        ),
    ]

    casos_invalidos = [
        ("usuario asignar admin",          "falta nombre de usuario"),
        ("mfa juan volar",                 "estado_mfa inválido"),
        ("login juan",                     "falta password"),
        ("permitir admin borrar usuarios", "acción inexistente"),
        ("denegar invitado eliminar red",  "recurso inexistente"),
    ]

    print("=" * 50)
    print("CASOS VÁLIDOS")
    print("=" * 50)
    for caso in casos_validos:
        print(f"\nEntrada: {repr(caso)}")
        try:
            ast = parse(caso)
            print(ast)
        except SyntaxError as e:
            print(f"  ERROR inesperado → {e}")

    print("\n" + "=" * 50)
    print("CASOS INVÁLIDOS")
    print("=" * 50)
    for caso, descripcion in casos_invalidos:
        print(f"\nEntrada: {repr(caso)}  ({descripcion})")
        try:
            ast = parse(caso)
            print(f"  ERROR: debería fallar pero produjo → {ast}")
        except SyntaxError as e:
            print(f"  Detectado correctamente → {e}")
