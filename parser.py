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
#
# MANEJO Y RECUPERACIÓN DE ERRORES (modo pánico)
# -----------------------------------------------------------------------------
# A nivel de cada sentencia individual el parser sigue siendo un LL(1) estricto:
# consume() lanza SyntaxError ante el primer token inesperado, sin backtracking.
#
# La RECUPERACIÓN se implementa un nivel arriba, en parse_lista_sentencias():
# cuando una sentencia falla, el error se captura ahí (no se propaga), se
# reporta con su línea y mensaje orientado al usuario, y el parser entra en
# "modo pánico": descarta tokens hasta encontrar el próximo token que
# pertenezca a FIRST(<sentencia>) (el conjunto de sincronización) o hasta el
# fin de la entrada, y continúa analizando el resto del programa desde ahí.
#
# Esto permite que un solo error en la sentencia N no impida detectar y
# reportar errores adicionales en las sentencias N+1, N+2, etc., ni impida
# construir el AST de las sentencias que sí son válidas.
#
# Flujo completo:
#   Texto -> [Lexer] -> lista de tokens -> [Parser LL(1) + modo pánico]
#         -> (AST parcial, lista de errores)
# =============================================================================


# Conjunto de sincronización para el modo pánico: todo token que puede iniciar
# una <sentencia> según la gramática. Es exactamente FIRST(<sentencia>).
INICIO_SENTENCIA = {'ROL', 'USUARIO', 'LOGIN', 'LOGOUT', 'MFA', 'PERMITIR', 'DENEGAR'}


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
#               con recuperación de errores en modo pánico
# =============================================================================
class Parser:
    def __init__(self, tokens):
        # tokens: lista completa de tokens producida por el lexer
        # pos: índice del token que estamos analizando actualmente
        # errores: lista de mensajes de error recuperados durante el análisis
        self.tokens = tokens
        self.pos = 0
        self.errores = []

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
        en qué línea ocurrió el error y qué se esperaba vs qué llegó. Esta
        excepción es responsabilidad de quien orquesta la sentencia (ver
        parse_lista_sentencias) capturarla y decidir cómo recuperarse.
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
    #
    # Nota sobre recuperación: como parse_lista_sentencias() ya consume tokens
    # hasta el final en caso de error irrecuperable (no quedan más tokens en
    # FIRST(<sentencia>)), al volver aquí no deberían quedar tokens sobrantes
    # en el caso general. Si igualmente quedara alguno (defensivo), se reporta
    # como error adicional en lugar de abortar todo el análisis.
    #
    # FIRST(<programa>) = FIRST(<lista_sentencias>)
    #                   = { rol, usuario, login, logout, mfa, permitir, denegar }
    def parse_programa(self):
        sentencias = self.parse_lista_sentencias()
        if self.current() is not None:
            tok = self.current()
            self.errores.append(f"Línea {tok.lineno}: token inesperado '{tok.value}'")
        return Node('programa', sentencias=sentencias)

    # -------------------------------------------------------------------------
    # PRODUCCIÓN: <lista_sentencias> -> <sentencia> | <sentencia> <lista_sentencias>
    # -------------------------------------------------------------------------
    # Analiza una o más sentencias seguidas. El bucle while continúa mientras
    # haya tokens de inicio de sentencia disponibles, O mientras el parser
    # esté en modo pánico tratando de resincronizar tras un error.
    #
    # RECUPERACIÓN (modo pánico):
    #   1. Si parse_sentencia() lanza SyntaxError, se captura aquí mismo.
    #   2. El mensaje se guarda en self.errores (con línea incluida).
    #   3. Se descartan tokens uno a uno hasta encontrar el próximo token en
    #      INICIO_SENTENCIA (conjunto de sincronización) o hasta el fin de
    #      la entrada.
    #   4. El análisis continúa normalmente desde el punto de sincronización.
    #
    # La sentencia que falló NO se agrega al AST: la lista resultante de
    # sentencias contiene únicamente las que se reconocieron correctamente.
    #
    # FIRST(<lista_sentencias>) = { rol, usuario, login, logout, mfa, permitir, denegar }
    # FOLLOW(<lista_sentencias>) = { $ }
    def parse_lista_sentencias(self):
        sentencias = []

        while self.current() is not None and self.current().type in INICIO_SENTENCIA:
            inicio_pos = self.pos
            try:
                sentencias.append(self.parse_sentencia())
            except SyntaxError as e:
                self.errores.append(str(e))

                # Modo pánico: si por algún motivo no se avanzó ni un token
                # (no debería pasar, pero es una salvaguarda contra loops
                # infinitos), forzamos avanzar al menos uno.
                if self.pos == inicio_pos:
                    self.pos += 1

                # Sincronización: descartar tokens hasta el próximo inicio
                # de sentencia válido o hasta el fin de la entrada.
                while self.current() is not None and self.current().type not in INICIO_SENTENCIA:
                    self.pos += 1
                # El bucle exterior continúa desde aquí, intentando parsear
                # la siguiente sentencia como si nada hubiera pasado.

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
#
# INTERFAZ (cambio respecto a versiones anteriores):
#   Antes: parse(texto) devolvía el AST, o lanzaba SyntaxError ante el primer
#          error (abortando todo el análisis).
#   Ahora: parse(texto) SIEMPRE devuelve una tupla (ast, errores):
#
#     - ast: el árbol sintáctico construido con las sentencias reconocidas
#            correctamente (puede estar incompleto si hubo errores).
#     - errores: lista de strings con los mensajes de error recuperados,
#                cada uno con su línea y una descripción orientada al
#                usuario. Lista vacía si el programa es completamente válido.
#
# Esto refleja fielmente la consigna de la cátedra: "reconocer cadenas
# válidas, detectar errores, continuar el análisis cuando sea posible".
# El llamador decide qué hacer con (ast, errores) según su propio criterio
# (ver test_runner.py para la clasificación VALIDO / INVALIDO / PARCIAL).
def parse(texto):
    lexer.lineno = 1
    lexer.input(texto)
    tok_list = list(lexer)
    parser = Parser(tok_list)
    ast = parser.parse_programa()
    return ast, parser.errores


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

    # Casos totalmente inválidos: la única sentencia presente falla y no hay
    # tokens de sincronización después, por lo que el AST resultante queda
    # vacío (0 sentencias reconocidas) y se reporta 1 error.
    casos_invalidos = [
        ("usuario asignar admin",   "falta nombre de usuario"),
        ("mfa juan volar",          "estado_mfa invalido: 'volar' no es activar/desactivar"),
        ("login juan",              "falta password"),
        ("permitir admin",          "falta accion y recurso"),
        ("denegar",                 "falta identificador, accion y recurso"),
    ]

    # Casos de RECUPERACIÓN: múltiples sentencias en una sola entrada, donde
    # una o más sentencias intermedias son inválidas pero el resto del
    # programa sí se reconoce correctamente gracias al modo pánico.
    casos_recuperacion = [
        (
            "rol admin\n"
            "usuario asignar admin\n"          # sentencia inválida (falta nombre)
            "login juan password123"
        ),
        (
            "mfa juan volar\n"                 # sentencia inválida (estado_mfa)
            "rol admin\n"
            "permitir admin acceder dashboard"
        ),
        (
            "permitir admin acceder dashboard\n"
            "denegar\n"                        # sentencia inválida (falta todo)
            "logout juan\n"
            "mfa juan activar"
        ),
    ]

    print("=" * 50)
    print("CASOS VALIDOS")
    print("=" * 50)
    for caso in casos_validos:
        print(f"\nEntrada: {repr(caso)}")
        ast, errores = parse(caso)
        print(ast)
        if errores:
            print(f"  ERROR inesperado, se reportaron errores -> {errores}")

    print("\n" + "=" * 50)
    print("CASOS INVALIDOS")
    print("=" * 50)
    for caso, descripcion in casos_invalidos:
        print(f"\nEntrada: {repr(caso)}  ({descripcion})")
        ast, errores = parse(caso)
        if errores and not ast.attrs['sentencias']:
            print(f"  Detectado correctamente -> {errores}")
        else:
            print(f"  ERROR: deberia fallar por completo pero produjo -> {ast} / errores={errores}")

    print("\n" + "=" * 50)
    print("CASOS DE RECUPERACION (modo panico, multi-sentencia)")
    print("=" * 50)
    for caso in casos_recuperacion:
        print(f"\nEntrada:\n{caso}")
        ast, errores = parse(caso)
        print("\nErrores detectados y recuperados:")
        for err in errores:
            print(f"  - {err}")
        print("\nAST parcial (sentencias válidas reconocidas):")
        print(ast)